import json
import logging
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from pprint import pformat

from pathvalidate import sanitize_filename
from tqdm import tqdm

from modules import utils
from modules.border_replacerr import BorderReplacerr
from modules.database_cache import Database
from modules.logger import init_logger
from modules.media import Radarr, Server, Sonarr
from modules.settings import Settings
from progress import ProgressState


class PosterRenamerr:
    def __init__(self, payload):
        self.logger = logging.getLogger("PosterRenamerr")
        try:
            log_dir = Path(Settings.LOG_DIR.value) / Settings.POSTER_RENAMERR.value
            init_logger(
                self.logger,
                log_dir,
                "poster_renamerr",
                log_level=payload.log_level if payload.log_level else logging.INFO,
            )
            supported_options = ["black", "remove", "custom"]
            self.db = Database(self.logger)
            self.target_path = Path(payload.target_path)
            self.backup_dir = Path(Settings.ORIGINAL_POSTERS.value)
            if not self.backup_dir.exists():
                self.backup_dir.mkdir()
            self.source_directories = payload.source_dirs
            self.asset_folders = payload.asset_folders
            self.clean_assets = payload.clean_assets
            self.upload_to_plex = payload.upload_to_plex
            self.match_alt = payload.match_alt
            self.only_unmatched = payload.only_unmatched
            self.replace_border = payload.replace_border

            if payload.border_setting in supported_options:
                self.border_setting = payload.border_setting
            else:
                self.logger.warning(
                    f"Invalid border color setting: {payload.border_setting}. Border replacerr will not run."
                )
                self.border_setting = None
                self.replace_border = False
            if self.border_setting == "custom" or self.border_setting == "black":
                if payload.custom_color and utils.is_valid_hex_color(
                    payload.custom_color
                ):
                    self.custom_color = payload.custom_color
                else:
                    self.logger.warning(
                        f"Invalid hex color code: {payload.custom_color}. Border replacerr will not run."
                    )
                    self.custom_color = None
                    self.replace_border = False
            else:
                self.custom_color = ""
                self.replace_border = payload.replace_border

            self.border_replacerr = BorderReplacerr(custom_color=self.custom_color)
            self.plex_instances = utils.create_plex_instances(
                payload, Server, self.logger
            )
            self.radarr_instances, self.sonarr_instances = utils.create_arr_instances(
                payload, Radarr, Sonarr, self.logger
            )

        except Exception as e:
            self.logger.exception("Failed to initialize PosterRenamerr")
            raise e

    image_exts = {".png", ".jpg", ".jpeg"}

    # only need to compile this once
    poster_id_pattern = re.compile(r"[\[\{](imdb|tmdb|tvdb)-([a-zA-Z0-9]+)[\}\]]")
    year_pattern = re.compile(r"\b(19|20)\d{2}\b")

    # length to use as a prefix.  anything shorter than this will be used as-is
    prefix_length = 3

    ALL_SEASONS_NO_EPISODES = "ALL_SEASONS_NO_EPISODES"

    def preprocess_name(self, name: str) -> str:
        """
        Preprocess a name for consistent matching:
        - Convert to lowercase
        - Remove special characters
        - Remove common words
        """
        name = utils.remove_chars(name)

        # Convert to lowercase and remove special characters
        name = re.sub(r"[^a-zA-Z0-9\s]", "", name.lower())
        # Remove extra whitespace
        name = " ".join(name.split())

        # Optionally remove common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to"}
        # maybe for collections we need to _not_ do this? i.e. 'FX.jpg vs. FX Collection' - only an issue when a collection name is 1 or 2 chars...
        return "".join(word for word in name.split() if word not in common_words)

    def build_search_index(
        self, prefix_index, title, asset, asset_type, debug_items=None
    ):
        """
        Build an index of preprocessed movie names for efficient lookup
        Returns both the index and preprocessed forms
        """
        asset_type_processed_forms = prefix_index[asset_type]
        processed = self.preprocess_name(title)
        debug_build_index = (
            debug_items and len(debug_items) > 0 and processed in debug_items
        )

        if debug_build_index:
            self.logger.info("debug_build_search_index")
            self.logger.info(processed)
            self.logger.info(asset_type)
            self.logger.info(asset)

        # Store word-level index for partial matches
        words = processed.split()
        if debug_build_index:
            self.logger.info(words)

        # only need to do the first word here
        # also - store add to a prefix to expand possible matches
        for word in words:
            # if len(word) > 2 or len(words)==1:  # Only index words longer than 2 chars unless it's the only word
            if word not in asset_type_processed_forms:
                asset_type_processed_forms[word] = (
                    list()
                )  # maybe consider moving to dequeue?
            asset_type_processed_forms[word].append(asset)

            # also add the prefix.  if shorter than prefix_length then it was already added above.
            if len(word) > self.prefix_length:
                prefix = word[0 : self.prefix_length]
                if debug_build_index:
                    self.logger.info(prefix)
                if prefix not in asset_type_processed_forms:
                    asset_type_processed_forms[prefix] = list()
                asset_type_processed_forms[prefix].append(asset)
            break

        return

    def search_matches(self, prefix_index, movie_title, asset_type, debug_search=False):
        """search for matches in the index"""
        matches = list()

        processed_filename = self.preprocess_name(movie_title)
        asset_type_processed_forms = prefix_index[asset_type]

        if debug_search:
            self.logger.info("debug_search_matches")
            self.logger.info(processed_filename)

        words = processed_filename.split()
        if debug_search:
            self.logger.info(words)
        # Try word-level matches
        for word in words:
            # first add any prefix matches to the beginning of the list.
            if len(word) > self.prefix_length:
                prefix = word[0 : self.prefix_length]
                if debug_search:
                    self.logger.info(prefix)
                    self.logger.info(prefix in asset_type_processed_forms)

                if prefix in asset_type_processed_forms:
                    matches.extend(asset_type_processed_forms[prefix])

            # then add the full word matches as items.
            # TODO: is this even needed any more given everything would grab the prefix
            #       or maybe this is an else to the above?
            if word in asset_type_processed_forms:
                matches.extend(asset_type_processed_forms[word])
            if debug_search:
                self.logger.info(matches)
            break

        return matches

    def _log_banner(self, job_id):
        self.logger.info("\n" + "#" * 80)
        self.logger.info(f"### New PosterRenamerr Run - Job ID: '{job_id}'")
        self.logger.info("\n" + "#" * 80)

    def clean_cache(self) -> None:
        try:
            asset_files = [str(item) for item in Path(self.target_path).rglob("*")]
            cached_file_data = self.db.return_all_files()
            cached_file_paths = list(cached_file_data.keys())

            for item in cached_file_paths:
                if item not in asset_files:
                    self.db.delete_cached_file(item)
                    self.logger.debug(f"Cleaned {item} from database")
        except Exception as e:
            self.logger.error(f"Error cleaning cache: {e}")

    def clean_asset_dir(self, media_dict, collections_dict) -> None:
        try:
            cached_file_data = self.db.return_all_files()
            cached_file_paths = list(cached_file_data.keys())
            directories_to_clean = [self.target_path, self.backup_dir]
            asset_files = (
                item
                for dir_path in directories_to_clean
                for item in dir_path.rglob("*")
                if item.is_file()
            )
            expected_folders = {}
            for show in media_dict.get("shows", []):
                normalized = utils.remove_chars(show["folder"])
                expected_folders[normalized] = show["folder"]
            for movie in media_dict.get("movies", []):
                normalized = utils.remove_chars(movie["folder"])
                expected_folders[normalized] = movie["folder"]

            show_titles = set()
            title_to_seasons_without_files = {}
            for show in media_dict.get("shows", []):
                title = utils.remove_chars(show["folder"])
                show_titles.add(title)
                matched_seasons = show.get("matched_season_info", [])

                if matched_seasons:
                    seasons_without_files = title_to_seasons_without_files.setdefault(
                        title, []
                    )
                    has_at_least_one_season_with_episodes = False
                    for season in matched_seasons:
                        season_str = season.get("season", "")
                        has_episodes = season.get("has_episodes", False)
                        if has_episodes:
                            has_at_least_one_season_with_episodes = True
                            continue
                        seasons_without_files.append(season_str)
                    # if no seasons have episodes, mark this for the poster file as well
                    if not has_at_least_one_season_with_episodes:
                        seasons_without_files.append(self.ALL_SEASONS_NO_EPISODES)

            titles = (
                set(
                    utils.remove_chars(movie["folder"])
                    for movie in media_dict.get("movies", [])
                )
                .union(show_titles)
                .union(
                    set(
                        utils.remove_chars(collection.replace("/", ""))
                        for collection in collections_dict.get("movies", [])
                    )
                )
                .union(
                    set(
                        utils.remove_chars(collection.replace("/", ""))
                        for collection in collections_dict.get("shows", [])
                    )
                )
            )

            removed_asset_count = 0
            directories_to_remove = []

            if self.asset_folders:
                self.logger.info(
                    "Detected asset folder configuration. Attempting to remove invalid assets."
                )
            else:
                self.logger.info(
                    "Detected flat asset configuration. Attempting to remove invalid assets."
                )
            for item in asset_files:
                parent_dir = item.parent
                if self.asset_folders:
                    if parent_dir == self.target_path or parent_dir == self.backup_dir:
                        self.logger.info(f"Removing orphaned asset file --> {item}")
                        item.unlink()
                        removed_asset_count += 1
                    else:
                        asset_title = utils.remove_chars(parent_dir.name)
                        if asset_title not in titles:
                            directories_to_remove.append(parent_dir)
                            removed_asset_count += 1
                        elif (
                            asset_title in expected_folders
                            and parent_dir.name != expected_folders[asset_title]
                        ):
                            self.logger.debug(
                                f"Removing stale casing folder: {parent_dir.name} (expected: {expected_folders[asset_title]})"
                            )
                            directories_to_remove.append(parent_dir)
                            removed_asset_count += 1
                        else:
                            if asset_title in title_to_seasons_without_files:
                                self.remove_upload_data_for_orphaned_asset(
                                    cached_file_data,
                                    cached_file_paths,
                                    title_to_seasons_without_files,
                                    item,
                                    asset_title,
                                )

                else:
                    asset_pattern = re.search(r"^(.*?)(?:_.*)?$", item.stem)
                    if asset_pattern:
                        asset_title = utils.remove_chars(asset_pattern.group(1))
                        if asset_title not in titles:
                            self.logger.info(f"Removing orphaned asset file --> {item}")
                            item.unlink()
                            removed_asset_count += 1
                        else:
                            if asset_title in title_to_seasons_without_files:
                                self.remove_upload_data_for_orphaned_asset(
                                    cached_file_data,
                                    cached_file_paths,
                                    title_to_seasons_without_files,
                                    item,
                                    asset_title,
                                )

            for directory in set(directories_to_remove):
                self._remove_directory(directory)

            for dir_path in directories_to_clean:
                for sub_dir in dir_path.rglob("*"):
                    if sub_dir.is_dir() and not any(sub_dir.iterdir()):
                        sub_dir.rmdir()

            self.logger.info(
                f"Removed {removed_asset_count} items from asset directories."
            )

        except Exception as e:
            self.logger.error(f"Error cleaning assets: {e}")

    def remove_upload_data_for_orphaned_asset(
        self,
        cached_file_data,
        cached_file_paths,
        title_to_seasons_without_files,
        item,
        asset_title,
    ):
        if asset_title in title_to_seasons_without_files:
            for season in title_to_seasons_without_files[asset_title][:]:
                if (
                    item.stem.lower().endswith(season.lower())
                    or season == self.ALL_SEASONS_NO_EPISODES
                ) and str(item) in cached_file_paths:
                    file_cache_data = cached_file_data[str(item)]
                    if file_cache_data.get("uploaded_to_libraries", []):
                        self.logger.debug(
                            f"Removing upload data for data for orphaned asset file --> {item}"
                        )
                        self.db.remove_upload_data_for_file(str(item))
                        title_to_seasons_without_files[asset_title].remove(season)

    def _remove_directory(self, directory: Path):
        if directory.exists() and directory.is_dir():
            self.logger.info(f"Removing orphaned asset directory: {directory}")
            for sub_item in list(directory.iterdir()):
                if sub_item.is_file():
                    sub_item.unlink()
            if directory.exists():
                directory.rmdir()

    def get_source_files(self) -> dict[str, list[Path]]:
        source_directories = [Path(item) for item in self.source_directories]
        source_files = {}
        unique_files = set()

        with tqdm(
            total=len(source_directories), desc="Processing directories"
        ) as dir_progress:
            for source_dir in source_directories:
                if not source_dir.is_dir():
                    self.logger.warning(f"{source_dir} is not a valid directory.")
                    dir_progress.update(1)
                    continue
                for poster in source_dir.rglob("*"):
                    if not poster.is_file():
                        self.logger.error(f"{poster} is not a file")
                        continue
                    if poster.suffix.lower() not in self.image_exts:
                        self.logger.debug(f"⏩ Skipping non-image file: {poster}")
                        continue
                    if poster.name in unique_files:
                        # self.logger.debug(f"⏩ Skipping duplicate file: {poster}")
                        continue
                    unique_files.add(poster.name)
                    source_files.setdefault(source_dir, []).append(poster)

                if source_dir in source_files:
                    # Sort files alphabetically to make processing and matching more consistent
                    source_files[source_dir] = sorted(
                        source_files[source_dir], key=lambda x: x.as_posix().lower()
                    )
                dir_progress.update(1)

        return source_files

    def handle_movie_match(
        self, matched_movies, file, movie_data, movie_has_file, movie_status
    ):
        matched_movies[file] = {
            "has_file": movie_has_file,
            "status": movie_status,
            "match": movie_data,
        }

    def is_season_complete(self, show_seasons, show_data):
        return (
            not show_seasons
            and "series_poster_matched" in show_data
            and show_data["series_poster_matched"]
        )

    def handle_show_season_match(
        self, season, matched_shows, file, show_data, show_seasons
    ):
        season_has_episodes = season.get("has_episodes", None)
        matched_shows[file] = {
            "has_episodes": season_has_episodes,
            "match": show_data,
        }
        # remove to determine later if we have all of the seasons
        show_seasons.remove(season)

    def handle_show_series_match(
        self,
        matched_shows,
        file,
        show_status,
        show_has_episodes,
        show_seasons,
        show_data,
    ):
        matched_shows[file] = {
            "status": show_status,
            "has_episodes": show_has_episodes,
            "match": show_data,
        }
        show_data["series_poster_matched"] = True
        self.logger.debug(f"Show seasons: {show_seasons}")

    def get_common_id_sources(self, asset, media):
        common_id_sources = []
        if asset["media_ids"]:
            if media["media_ids"]:
                for media_id_source, _ in media["media_ids"].items():
                    if media_id_source in asset["media_ids"]:
                        common_id_sources.append(media_id_source)

        return common_id_sources

    def compare_asset_to_media(self, asset, media, special_debug=False):
        match = False
        has_year_match = False

        common_id_sources = self.get_common_id_sources(asset, media)
        if common_id_sources:
            for id_source in common_id_sources:
                id_match = (
                    asset["media_ids"][id_source] == media["media_ids"][id_source]
                )
                self.logger.debug(
                    f"both sides shared a common id! do they match? {id_match} ... asset_ids= {asset['media_ids']}, media_ids= {media['media_ids']}"
                )
                # if the current source existed but didn't match, but there are still other IDs to consider - keep looping
                if id_match:
                    return True
            # at this point we know there were common sources and if any had matched we would have short circuited above.
            self.logger.debug(
                f"both sides shared a common id! but none matched ... asset_ids= {asset['media_ids']}, media_ids= {media['media_ids']}"
            )
            return False

        has_year_match = (
            media["item_year"] is None and asset["item_year"] is None
        ) or (media["item_year"] == asset["item_year"])
        if not has_year_match:
            # no media years (collection) but asset has some year value
            if "media_item_years" not in media and asset["item_year"] is not None:
                return False

            # no media years (collection) and asset also doesn't have years (collection)
            if "media_item_years" not in media and asset["item_year"] is None:
                self.logger.debug("matching_year")
                has_year_match = True

            if "media_item_years" in media:
                for year in media["media_item_years"]:
                    if year == asset["item_year"]:
                        has_year_match = True
                        break
        match = (
            asset["sanitized_name_without_extension"]
            == media["sanitized_name_without_extension"]
            or asset["extra_sanitized_name_without_extension"]
            == media["extra_sanitized_name_without_extension"]
            or asset["sanitized_name_without_collection"]
            == media["sanitized_name_without_collection"]
            or asset["extra_sanitized_name_without_collection"]
            == media["extra_sanitized_name_without_collection"]
            or asset["sanitized_no_spaces"] == media["sanitized_no_spaces"]
            or asset["extra_sanitized_no_spaces"] == media["extra_sanitized_no_spaces"]
            or asset["sanitized_no_spaces_no_collection"]
            == media["sanitized_no_spaces_no_collection"]
            or asset["extra_sanitized_no_spaces_no_collection"]
            == media["extra_sanitized_no_spaces_no_collection"]
            or (
                asset["has_season_info"]
                and asset["extra_sanitized_no_spaces_no_seasons_specials"]
                == media["extra_sanitized_no_spaces_no_collection"]
            )
        ) and (
            # movies/collections will always match here
            asset["has_season_info"] == media["has_season_info"]
            or
            # the asset could be a season/specials and we match to the show
            (asset["has_season_info"] and "show_seasons" in media)
        )

        if special_debug:
            self.logger.debug(f"asset: {asset}")
            self.logger.debug(f"media: {media}")
            self.logger.debug(f"match= {match}")
            self.logger.debug(f"has_year_match= {has_year_match}")

        return match and has_year_match

    def compute_variations_for_comparisons(
        self, orig_string, object_to_populate
    ) -> None:
        lowered_orig_string = orig_string.lower()
        stripped_id = utils.strip_id(lowered_orig_string)
        stripped_year = utils.strip_year(stripped_id)
        sanitized_name_without_extension = utils.remove_chars(stripped_year)

        # handle some countries being included in names.
        extra_sanitized_name_without_extension = re.sub(
            r"\((us|uk|au|ca|nz|fr)\)", "", stripped_year
        )
        extra_sanitized_name_without_extension = utils.remove_chars(
            extra_sanitized_name_without_extension
        )

        # replace certain prefixes
        extra_sanitized_name_without_extension = re.sub(
            r"^\b{}\b".format("(the|a|an)"), "", extra_sanitized_name_without_extension
        )

        object_to_populate["name_without_extension"] = lowered_orig_string
        object_to_populate["sanitized_name_without_extension"] = (
            sanitized_name_without_extension
        )
        object_to_populate["extra_sanitized_name_without_extension"] = (
            extra_sanitized_name_without_extension
        )
        object_to_populate["sanitized_name_without_collection"] = object_to_populate[
            "sanitized_name_without_extension"
        ].removesuffix(" collection")
        object_to_populate["extra_sanitized_name_without_collection"] = (
            object_to_populate["extra_sanitized_name_without_extension"].removesuffix(
                " collection"
            )
        )
        # strip all spaces out
        object_to_populate["sanitized_no_spaces"] = re.sub(
            r"\W+", "", object_to_populate["sanitized_name_without_extension"]
        )
        object_to_populate["extra_sanitized_no_spaces"] = re.sub(
            r"\W+", "", object_to_populate["extra_sanitized_name_without_extension"]
        )
        object_to_populate["sanitized_no_spaces_no_collection"] = re.sub(
            r"\W+", "", object_to_populate["sanitized_name_without_collection"]
        )
        object_to_populate["extra_sanitized_no_spaces_no_collection"] = re.sub(
            r"\W+", "", object_to_populate["extra_sanitized_name_without_collection"]
        )
        year_match = re.search(
            r"\((\d{4})\)", lowered_orig_string
        )  # should we improve this ?
        object_to_populate["has_season_info"] = bool(
            re.search(r" - (season|specials)", lowered_orig_string)
        )
        object_to_populate["item_year"] = year_match.group(1) if year_match else None
        all_item_ids = self.poster_id_pattern.findall(lowered_orig_string)
        # dict of <media_id_source> --> <media_id>
        media_ids = {}
        for item_id_match in all_item_ids:
            media_ids[item_id_match[0]] = item_id_match[1]
        object_to_populate["media_ids"] = media_ids

        season_num_match = re.search(r"- season (\d+)", lowered_orig_string)
        object_to_populate["season_num"] = (
            int(season_num_match.group(1)) if season_num_match else None
        )
        if object_to_populate["has_season_info"]:
            object_to_populate["extra_sanitized_no_spaces_no_seasons_specials"] = (
                re.sub(
                    r"(specials|season(\d+))$",
                    "",
                    object_to_populate["extra_sanitized_no_spaces_no_collection"],
                ).strip()
            )

    def compute_asset_values_for_match(self, search_match) -> None:
        file = search_match[
            "file"
        ]  # given a search match we can pre-compute (& store) values
        # this will compute values if they don't already exist and put them back onto the search match.
        if "computed_attributes" not in search_match:
            search_match["computed_attributes"] = True
            # from here down it's just a string...
            self.compute_variations_for_comparisons(file.stem.lower(), search_match)

    def merge_stats_into_overall_asset_stats(
        self, overall_asset_stats, single_item_stats
    ):
        for key in overall_asset_stats:
            overall_asset_stats[key] += (
                single_item_stats[key] if key in single_item_stats else 0
            )

    def match_files_with_media(
        self,
        source_files: dict[str, list[Path]],
        media_dict: dict[str, list],
        collections_dict: dict[str, list[str]],
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
    ) -> dict[str, dict[Path, str | bool]]:
        matched_files = {"collections": [], "movies": {}, "shows": {}, "dups": {}}
        flattened_col_list = [
            item for sublist in collections_dict.values() for item in sublist
        ]
        movies_list_copy = media_dict.get("movies", [])[:]
        shows_list_copy = media_dict.get("shows", [])[:]

        processed_files = 0
        total_files = (
            len(movies_list_copy) + len(flattened_col_list) + len(shows_list_copy)
        )

        # dict per asset type to map asset prefixes to the assets, themselves.
        prefix_index = {
            "movies": {},
            "shows": {},
            "collections": {},
            "all": {},  # for now using this as "catch all"
        }

        self.index_all_asset_files(source_files, prefix_index)

        with tqdm(
            total=total_files, desc="Processing media files for matches"
        ) as progress_bar:
            ################ PROCESS COLLECTIONS ################
            overall_collection_stats = {
                "matched_collections": 0,
                "unmatched_collections": 0,
                "collections_alt_title_searches_performed": 0,
                "collections_matches_found_with_alt_title_searches": 0,
            }
            for collection_name in flattened_col_list[:]:
                # for collections they are a bit "special" in that it could be x.jpg or x collection.jpg on the file and the prefix of those two
                # files in the index is different.  So for a collection we effectively want to search for the main version to start
                # and then fall back to the other variation.  This is effectively mimicking alternate title searching.
                variations_to_search = self.get_title_variations_for_collections(
                    collection_name
                )

                single_collection_stats = self.match_collection_with_files(
                    matched_files, prefix_index, collection_name, variations_to_search
                )
                self.merge_stats_into_overall_asset_stats(
                    overall_collection_stats, single_collection_stats
                )
                processed_files += 1
                self.update_progress(
                    cb, job_id, processed_files, total_files, progress_bar
                )

            ################ PROCESS MOVIES ################
            overall_movie_stats = {
                "matched_movies": 0,
                "unmatched_movies": 0,
                "movies_alt_title_searches_performed": 0,
                "movies_matches_found_with_alt_title_searches": 0,
            }
            for movie_data in movies_list_copy[:]:
                alt_titles_clean = self.get_alt_titles_from_media_item(movie_data)

                titles_to_search = [movie_data.get("title", "")]
                # append alt titles to the end.  Will only be used if the main title search isn't found
                titles_to_search.extend(alt_titles_clean)

                single_movie_stats = self.match_movie_with_files(
                    matched_files, prefix_index, movie_data, titles_to_search
                )
                self.merge_stats_into_overall_asset_stats(
                    overall_movie_stats, single_movie_stats
                )

                processed_files += 1
                self.update_progress(
                    cb, job_id, processed_files, total_files, progress_bar
                )

            ################ PROCESS SHOWS ################
            overall_show_stats = {
                "fully_matched_shows": 0,
                "unmatched_shows": 0,
                "partial_matched_shows": 0,
                "partial_matched_missing_seasons": 0,
                "partial_matched_missing_poster": 0,
                "partial_matched_only_missing_specials": 0,
                "shows_matches_found_with_alt_title_searches": 0,
                "shows_alt_title_searches_performed": 0,
            }
            for show_data in shows_list_copy[:]:
                alt_titles_clean = self.get_alt_titles_from_media_item(show_data)

                titles_to_search = [show_data.get("title", "")]
                # append alt titles to the end.  Will only be used if the main title search isn't found
                titles_to_search.extend(alt_titles_clean)

                single_show_stats = self.match_show_with_files(
                    matched_files, prefix_index, titles_to_search, show_data
                )
                self.merge_stats_into_overall_asset_stats(
                    overall_show_stats, single_show_stats
                )

                processed_files += 1
                self.update_progress(
                    cb, job_id, processed_files, total_files, progress_bar
                )

        self.logger.info(f"collection matching stats: {overall_collection_stats}")
        self.logger.info(f"movie matching stats: {overall_movie_stats}")
        self.logger.info(f"show matching stats: {overall_show_stats}")
        if matched_files["dups"]:
            self.logger.info("DUPLICATE ASSET MATCHES DETECTED")
            self.logger.info(json.dumps(matched_files["dups"], indent=4))
            matched_files["dups"] = (
                None  # clear this out so that it's not repeated below
            )
        self.logger.debug("Matched files summary:")
        self.logger.debug(pformat(matched_files))

        return matched_files

    def index_all_asset_files(self, source_files, prefix_index):
        total_directories = len(source_files)
        items_indexed = 0
        with tqdm(
            total=total_directories, desc="Processing directories"
        ) as progress_bar:
            for directory, files in source_files.items():
                self.logger.info(f"Processing directory: {directory}")
                for file in files:
                    name_without_extension = file.stem
                    # could add an id --> file lookup here :-)
                    # not building an asset type index here yet since we process assets on-the-fly
                    # everything will be placed into the 'all' asset type for now
                    file_ref = {"file": file}
                    self.build_search_index(
                        prefix_index,
                        name_without_extension,
                        file_ref,
                        "all",
                        debug_items=None,
                    )
                    items_indexed += 1
                progress_bar.update(1)
            self.logger.info(
                f"all directories processed and index is built. Found {items_indexed} posters"
            )

    def update_progress(self, cb, job_id, processed_files, total_files, progress_bar):
        progress_bar.update(1)
        if job_id and cb:
            progress = int((processed_files / total_files) * 70)
            cb(job_id, progress + 10, ProgressState.IN_PROGRESS)

    def get_title_variations_for_collections(self, collection_name):
        variations_to_search = [collection_name]
        lower_collection_name = collection_name.lower()
        if lower_collection_name.endswith(" collection"):
            variations_to_search.append(
                lower_collection_name.removesuffix(" collection")
            )
        else:
            variations_to_search.append(lower_collection_name + " collection")
        return variations_to_search

    def match_show_with_files(
        self, matched_files, prefix_index, titles_to_search, show_data
    ):
        stats = {
            "fully_matched_shows": 0,
            "unmatched_shows": 0,
            "partial_matched_shows": 0,
            "partial_matched_missing_seasons": 0,
            "partial_matched_missing_poster": 0,
            "partial_matched_only_missing_specials": 0,
            "shows_matches_found_with_alt_title_searches": 0,
            "shows_alt_title_searches_performed": 0,
        }

        shows_main_title_search = True
        self.logger.debug(f"titles_to_search: {titles_to_search}")
        found_a_match = False
        for title in titles_to_search:
            if shows_main_title_search:
                self.logger.debug(
                    f"doing main title search for {show_data.get('title', '')} of: {title}"
                )
            else:
                stats["shows_alt_title_searches_performed"] += 1
                self.logger.debug(
                    f"doing alt title search for {show_data.get('title', '')} of: {title}"
                )
            matched_show_files = self.find_series_matches(
                prefix_index, title, show_data, matched_files["dups"]
            )
            num_matches = len(matched_show_files["shows"])
            matched_entire_show = matched_show_files["matched_entire_show"]
            # this will have been updated from within the lookup function.
            if num_matches > 0:
                if not shows_main_title_search:
                    stats["shows_matches_found_with_alt_title_searches"] += 1
                found_a_match = True
                matched_files["shows"] = (
                    matched_files["shows"] | matched_show_files["shows"]
                )

                # if we found a match, but it wasn't the entire show, let's get some stats
                if not matched_entire_show:
                    self.logger.debug(f"partial_match encountered {show_data}")
                    stats["partial_matched_shows"] += 1
                    show_seasons = show_data.get("seasons", [])
                    for season in show_seasons:
                        if (
                            "season00" in season.get("season", "")
                            and len(show_seasons) == 1
                        ):
                            stats["partial_matched_only_missing_specials"] += 1
                        if season["has_episodes"]:
                            stats["partial_matched_missing_seasons"] += 1
                            break
                    if "series_poster_matched" not in show_data or (
                        "series_poster_matched" in show_data
                        and not show_data["series_poster_matched"]
                    ):
                        stats["partial_matched_missing_poster"] += 1
                else:
                    stats["fully_matched_shows"] += 1
                break  # if we found any match then we stop here vs. searching for alt titles
            shows_main_title_search = False

        if not found_a_match:
            stats["unmatched_shows"] += 1
            self.logger.info(f"No match found for show {show_data.get('title', '')}")
        return stats

    def match_collection_with_files(
        self, matched_files, prefix_index, collection_name, variations_to_search
    ):
        stats = {
            "matched_collections": 0,
            "unmatched_collections": 0,
            "collections_alt_title_searches_performed": 0,
            "collections_matches_found_with_alt_title_searches": 0,
        }

        found_matching_collection = False
        collections_main_title_search = True
        for collection_name_to_search in variations_to_search:
            if not collections_main_title_search:
                stats["collections_alt_title_searches_performed"] += 1
            matched_collection_files = self.find_collection_matches(
                prefix_index,
                collection_name_to_search,
                collection_name,
                matched_files["dups"],
            )
            num_matches = len(matched_collection_files["collections"])
            if num_matches > 0:
                found_matching_collection = True
                stats["matched_collections"] += 1
                if not collections_main_title_search:
                    stats["collections_matches_found_with_alt_title_searches"] += 1
                matched_files["collections"].extend(
                    matched_collection_files["collections"]
                )
                break
            collections_main_title_search = False
        if not found_matching_collection:
            stats["unmatched_collections"] += 1
            self.logger.info(f"No match found for collection {collection_name}")
        return stats

    def match_movie_with_files(
        self, matched_files, prefix_index, movie_data, titles_to_search
    ):
        stats = {
            "matched_movies": 0,
            "unmatched_movies": 0,
            "movies_alt_title_searches_performed": 0,
            "movies_matches_found_with_alt_title_searches": 0,
        }
        movies_main_title_search = True
        self.logger.debug(f"titles_to_search: {titles_to_search}")
        found_a_match = False
        for title in titles_to_search:
            if movies_main_title_search:
                self.logger.debug(
                    f"doing main title search for {movie_data.get('title', '')} of: {title}"
                )
            else:
                stats["movies_alt_title_searches_performed"] += 1
                self.logger.debug(
                    f"doing alt title search for {movie_data.get('title', '')} of: {title}"
                )

            matched_movie_files = self.find_movie_matches(
                prefix_index, title, movie_data, matched_files["dups"]
            )
            num_matches = len(matched_movie_files["movies"])
            if num_matches > 0:
                stats["matched_movies"] += 1
                if not movies_main_title_search:
                    stats["movies_matches_found_with_alt_title_searches"] += 1
                    # merge the new match with existing matches
                matched_files["movies"] = (
                    matched_files["movies"] | matched_movie_files["movies"]
                )
                found_a_match = True
                break
            movies_main_title_search = False
        if not found_a_match:
            stats["unmatched_movies"] += 1
            self.logger.info(f"No match found for movie {movie_data.get('title', '')}")
        return stats

    def get_alt_titles_from_media_item(self, media_item):
        if self.match_alt:
            alt_titles_clean = [
                utils.remove_chars(alt)
                for alt in media_item.get("alternate_titles", [])
            ]
            item_year = re.search(r"\((\d{4})\)", media_item.get("title", ""))
            if item_year:
                alt_titles_clean = [
                    alt
                    if self.year_pattern.search(alt)
                    else f"{alt} ({item_year.group(1)})"
                    for alt in alt_titles_clean
                ]
        else:
            alt_titles_clean = []
        return alt_titles_clean

    def find_series_matches(self, prefix_index, search_title, show_data, dups_dict):
        matched_files = {
            "shows": {},
            "matched_entire_show": False,
        }

        show_name = show_data.get("title", "")
        show_status = show_data.get("status", "")
        show_seasons = show_data.get("seasons", [])
        show_has_episodes = show_data.get("has_episodes", None)

        media_object = {}
        self.compute_variations_for_comparisons(search_title, media_object)
        media_object["show_status"] = show_status
        media_object["show_seasons"] = show_seasons
        local_debug = self.check_debug_mode(media_object)
        prior_level = self.logger.getEffectiveLevel()
        if local_debug:
            self.logger.info(
                f"changing log level from {prior_level} to {logging.DEBUG}"
            )
            self.logger.setLevel(logging.DEBUG)
            for handler in self.logger.handlers:
                handler.setLevel(logging.DEBUG)

        search_matches = self.search_matches(
            prefix_index, search_title, "all", debug_search=False
        )
        self.logger.debug(
            f"SEARCH (shows): matched assets for {show_data.get('title', '')} with query {search_title}"
        )
        self.logger.debug(f"show_data: {show_data}")
        self.logger.debug(f"search_matches: {search_matches}")

        # really inefficient for now but I have to ensure we loop over _ever single match since seasons are calculated on the fly based on the files
        # this is expensive - especially since we don't remove items from the match list (though we could....)
        # the better solution is not to remove things but instead to pre-calculate seasons based on the asset files and then when you match you get everything in one shot
        matched_entire_show = False
        matched_poster = False
        for search_match in search_matches:
            self.compute_asset_values_for_match(search_match)
            file = search_match["file"]
            extra_sanitized_no_spaces_no_collection = search_match[
                "extra_sanitized_no_spaces_no_collection"
            ]
            poster_file_year = search_match["item_year"]
            has_season_info = search_match["has_season_info"]
            season_num = search_match["season_num"]

            if not poster_file_year:
                self.logger.debug(f"Skipping collection file: '{file}'")
                continue  # it's a collection, skip it.

            matched_season = False
            matched_previously_matched_item = False

            special_asset = extra_sanitized_no_spaces_no_collection.endswith("specials")
            if self.compare_asset_to_media(
                search_match, media_object, special_debug=local_debug
            ):
                if season_num or has_season_info:
                    self.logger.debug(
                        f"found a season num ({season_num}) for file {file}, trying to match_show_season"
                    )
                    for season in show_seasons[:]:
                        season_str = season.get("season", "")
                        season_str_match = re.match(r"season(\d+)", season_str)
                        if season_str_match:
                            media_season_num = int(season_str_match.group(1))
                            if (season_num == media_season_num) or (
                                special_asset and "season00" in season_str
                            ):
                                if "previously_matched" in search_match:
                                    self.handle_previously_matched_asset(
                                        dups_dict,
                                        "shows",
                                        show_name,
                                        search_match,
                                        file,
                                    )
                                    matched_previously_matched_item = True
                                    continue
                                self.logger.debug(
                                    f"Matched season {media_season_num} for show: {show_name} with {file}"
                                )
                                self.handle_show_season_match(
                                    season,
                                    matched_files["shows"],
                                    file,
                                    show_data,
                                    show_seasons,
                                )
                                matched_season = True
                                matched_season_info = show_data.setdefault(
                                    "matched_season_info", []
                                )
                                matched_season_info.append(season)
                                search_match["previously_matched"] = (
                                    f"shows: {show_name}"
                                )
                                break  # this break is fine
                    if matched_previously_matched_item:
                        continue
                    if matched_season:
                        if self.is_season_complete(show_seasons, show_data):
                            self.logger.debug(
                                f"All seasons and series poster matched for {show_name}"
                            )
                            matched_entire_show = True
                            break  # can stop looping if we have everything
                        continue  # otherwise keep looping

                # deal with show poster matches if we don't already have one
                if not matched_season and not has_season_info and not matched_poster:
                    self.logger.debug(f"no match yet for file {file}, trying again...")
                    if "previously_matched" in search_match:
                        matched_previously_matched_item = True
                        self.handle_previously_matched_asset(
                            dups_dict, "shows", show_name, search_match, file
                        )
                        continue

                    search_match["previously_matched"] = f"shows: {show_name}"
                    matched_poster = True
                    self.logger.debug(
                        f"Matched series poster for show: {show_name} with {file}"
                    )
                    self.handle_show_series_match(
                        matched_files["shows"],
                        file,
                        show_status,
                        show_has_episodes,
                        show_seasons,
                        show_data,
                    )
                    if self.is_season_complete(show_seasons, show_data):
                        self.logger.debug(
                            f"All seasons and series poster matched for {show_name}"
                        )
                        matched_entire_show = True
                        break  # can stop looping if we have everything
                    continue  # otherwise keep looping

            if matched_entire_show:
                break  # stop everything.

        matched_files["matched_entire_show"] = matched_entire_show
        self.logger.setLevel(prior_level)
        for handler in self.logger.handlers:
            handler.setLevel(prior_level)

        return matched_files

    def check_debug_mode(self, media_object):
        enable_debug = False
        search_debug_string = os.environ.get("SEARCH_DEBUG", None)
        if search_debug_string:
            debug_strings = search_debug_string.split("|")
            for debug_string in debug_strings:
                debug_string = debug_string.strip()
                if (
                    len(debug_string) > 1
                    and debug_string
                    in media_object["extra_sanitized_no_spaces_no_collection"]
                ):
                    enable_debug = True
                    self.logger.info("ENABLE_SPECIAL_DEBUG!!")
                    break
        return enable_debug

    def find_movie_matches(self, prefix_index, search_title, movie_data, dups_dict):
        matched_files = {
            "movies": {},
        }
        movie_title = movie_data.get("title", "")
        movie_years = movie_data.get("years", [])
        movie_status = movie_data.get("status", "")
        movie_has_file = movie_data.get("has_file", None)

        media_object = {}
        self.compute_variations_for_comparisons(search_title, media_object)
        media_object["media_item_years"] = movie_years
        local_debug = self.check_debug_mode(media_object)
        prior_level = self.logger.getEffectiveLevel()
        if local_debug:
            self.logger.info(
                f"changing log level from {prior_level} to {logging.DEBUG}"
            )
            self.logger.setLevel(logging.DEBUG)
            for handler in self.logger.handlers:
                handler.setLevel(logging.DEBUG)

        search_matches = self.search_matches(
            prefix_index, search_title, "all", debug_search=False
        )
        self.logger.debug(
            f"SEARCH (movies): matched assets for {movie_data.get('title', '')} with query {search_title}"
        )
        self.logger.debug(search_matches)

        for search_match in search_matches:
            self.compute_asset_values_for_match(search_match)
            file = search_match["file"]
            poster_file_year = search_match["item_year"]
            has_season_info = search_match["has_season_info"]

            if poster_file_year and not has_season_info:
                if self.compare_asset_to_media(
                    search_match, media_object, special_debug=local_debug
                ):
                    if "previously_matched" in search_match:
                        self.handle_previously_matched_asset(
                            dups_dict, "movies", movie_title, search_match, file
                        )
                        continue
                    self.logger.debug(
                        f"Found match for movie: {movie_title} with {file}"
                    )
                    self.handle_movie_match(
                        matched_files["movies"],
                        file,
                        movie_data,
                        movie_has_file,
                        movie_status,
                    )
                    search_match["previously_matched"] = f"movies: {movie_title}"
                    break  # found a match break the search match loop

        self.logger.setLevel(prior_level)
        for handler in self.logger.handlers:
            handler.setLevel(prior_level)

        return matched_files

    def handle_previously_matched_asset(
        self, dups_dict, asset_type, movie_title, search_match, file
    ):
        file_string = str(file)
        if file not in dups_dict:
            dups_dict[file_string] = []
            dups_dict[file_string].append(f"{search_match['previously_matched']}")
        dups_dict[file_string].append(f"{asset_type}: {movie_title}")
        self.logger.info(
            f"{asset_type}: asset {file} would have matched {movie_title} but it previously matched {search_match['previously_matched']}"
        )

    # need to return some data here... prob just a boolean for "did we find a match"
    def find_collection_matches(
        self, prefix_index, collection_name_to_search, collection_name, dups_dict
    ):
        matched_files = {
            "collections": [],
        }
        media_object = {}
        self.compute_variations_for_comparisons(collection_name_to_search, media_object)

        local_debug = self.check_debug_mode(media_object)
        prior_level = self.logger.getEffectiveLevel()
        if local_debug:
            self.logger.info(
                f"changing log level from {prior_level} to {logging.DEBUG}"
            )
            self.logger.setLevel(logging.DEBUG)
            for handler in self.logger.handlers:
                handler.setLevel(logging.DEBUG)

        search_matches = self.search_matches(
            prefix_index,
            collection_name_to_search,
            "all",
            debug_search=False,
        )
        self.logger.debug(
            f"SEARCH (collections): matched assets for {collection_name} with query {collection_name_to_search}"
        )
        self.logger.debug(search_matches)
        for search_match in search_matches:
            self.compute_asset_values_for_match(search_match)
            file = search_match["file"]
            poster_file_year = search_match["item_year"]
            has_season_info = search_match["has_season_info"]

            if not poster_file_year and not has_season_info:
                # already know we're in collections... but the above check could still be true
                # since we're looping over matches across all asset types...

                if self.compare_asset_to_media(
                    search_match, media_object, special_debug=local_debug
                ):
                    if "previously_matched" in search_match:
                        self.handle_previously_matched_asset(
                            dups_dict,
                            "collections",
                            collection_name,
                            search_match,
                            file,
                        )
                        continue
                    collection_object = {"file": file}
                    collection_object["match"] = collection_name
                    matched_files["collections"].append(collection_object)
                    search_match["previously_matched"] = (
                        f"collections: {collection_name}"
                    )
                    self.logger.debug(
                        f"Matched collection poster for {collection_name} with {file}"
                    )
                    break
        self.logger.setLevel(prior_level)
        for handler in self.logger.handlers:
            handler.setLevel(prior_level)

        return matched_files

    def _match_id(self, file_name: str, media_name: str, poster_id_pattern: re.Pattern):
        poster_id_match = poster_id_pattern.search(file_name)
        media_id_match = poster_id_pattern.search(media_name)

        if poster_id_match and media_id_match:
            return poster_id_match.group(0) == media_id_match.group(0)

        return False

    def get_unmatched_media_dict(self) -> dict[str, list]:
        media_dict = {"movies": [], "shows": []}
        unmatched_show_arr_ids = self.db.get_unmatched_arr_ids("unmatched_shows")
        unmatched_movie_arr_ids = self.db.get_unmatched_arr_ids("unmatched_movies")

        for arr_id, instance_name in unmatched_movie_arr_ids:
            instance = self.radarr_instances.get(instance_name)
            if instance:
                try:
                    media_dict["movies"].extend(instance.get_movie(arr_id))
                except Exception as e:
                    self.logger.error(
                        f"Failed to fetch movie with ID {arr_id} from instance '{instance_name}': {e}"
                    )
            else:
                self.logger.error(f"No Radarr instance found for '{instance_name}'")

        for arr_id, instance_name in unmatched_show_arr_ids:
            instance = self.sonarr_instances.get(instance_name)
            if instance:
                try:
                    media_dict["shows"].extend(instance.get_show(arr_id))
                except Exception as e:
                    self.logger.error(
                        f"Failed to fetch show with ID {arr_id} from instance '{instance_name}': {e}"
                    )
            else:
                self.logger.error(f"No Sonarr instance found for '{instance_name}'")

        return media_dict

    def get_unmatched_collections_dict(self):
        collections_dict = {"all_collections": []}
        unmatched_collections = self.db.get_unmatched_assets("unmatched_collections")
        for collection in unmatched_collections:
            if "title" in collection:
                collections_dict["all_collections"].append(collection["title"])
        return collections_dict

    def log_matched_file(
        self, asset_type: str, name: str, file_name: str, season_special_name: str = ""
    ) -> None:
        """Log a matched file with a structured format."""
        if asset_type.lower() in {"season", "special"}:
            self.logger.debug(
                f"""
            -------------------------------------------------------
            Matched {asset_type.capitalize()}:
                - Show name: {name}
                - {asset_type.capitalize()}: {season_special_name}
                - File: {file_name}
            -------------------------------------------------------
            """
            )
        else:
            self.logger.debug(
                f"""
            -------------------------------------------------------
            Matched {asset_type.capitalize()}:
                - {asset_type.capitalize()}: {name}
                - File: {file_name}
            -------------------------------------------------------
            """
            )

    def _copy_file(
        self,
        file_path: Path,
        media_type: str,
        target_dir: Path,
        backup_dir: Path | None,
        new_file_name: str,
        replace_border: bool = False,
        status: str | None = None,
        has_episodes: bool | None = None,
        has_file: bool | None = None,
        webhook_run: bool | None = None,
        arr_id: int | None = None,
        instance: str | None = None,
        imdb_id: str | None = None,
        tmdb_id: str | None = None,
        tvdb_id: str | None = None,
    ) -> None:
        temp_path = None
        target_path = target_dir / new_file_name
        if backup_dir:
            backup_path = backup_dir / new_file_name
        else:
            backup_path = self.backup_dir / new_file_name
        file_name_without_extension = target_path.stem
        original_file_hash = utils.hash_file(file_path, self.logger)
        cached_file = self.db.get_cached_file(str(target_path))
        current_source = str(file_path)

        if target_path.exists() and cached_file:
            cached_hash = cached_file["file_hash"]
            cached_original_hash = cached_file["original_file_hash"]
            cached_source = cached_file["source_path"]
            cached_border_state = cached_file.get("border_replaced", 0)
            cached_border_setting = cached_file.get("border_setting", None)
            cached_custom_color = cached_file.get("custom_color", None)
            cached_has_episodes = cached_file.get("has_episodes", None)
            cached_has_file = cached_file.get("has_file", None)
            cached_status = cached_file.get("status", None)
            cached_arr_id = cached_file.get("arr_id", None)
            cached_instance = cached_file.get("instance", None)
            cached_imdb_id = cached_file.get("imdb_id", None)
            cached_tmdb_id = cached_file.get("tmdb_id", None)
            cached_tvdb_id = cached_file.get("tvdb_id", None)

            # Debugging: Log the current and cached values for comparison
            self.logger.debug(f"Checking skip conditions for file: {file_path}")
            self.logger.debug(f"File name: {file_name_without_extension}")
            self.logger.debug(f"Original file hash: {original_file_hash}")
            self.logger.debug(f"Cached hash: {cached_hash}")
            self.logger.debug(f"Cached original hash: {cached_original_hash}")
            self.logger.debug(f"Current source: {current_source}")
            self.logger.debug(f"Cached source: {cached_source}")
            self.logger.debug(f"Replace border (current): {replace_border}")
            self.logger.debug(f"Cached border replaced: {cached_border_state}")
            self.logger.debug(f"Cached border color: {cached_border_setting}")
            self.logger.debug(f"Current border color: {self.border_setting}")
            self.logger.debug(f"Cached custom color: {cached_custom_color}")
            self.logger.debug(f"Current custom color: {self.custom_color}")
            self.logger.debug(f"Cached status: {cached_status}")
            self.logger.debug(f"Current status: {status}")
            self.logger.debug(f"Cached has_episodes: {cached_has_episodes}")
            self.logger.debug(f"Current has_episodes: {has_episodes}")
            self.logger.debug(f"Cached has_file: {cached_has_file}")
            self.logger.debug(f"Current has_file: {has_file}")

            if cached_has_episodes is None or cached_has_episodes != has_episodes:
                if has_episodes is not None:
                    self.logger.debug(
                        f"Updating 'has_episodes' for {target_path}: {cached_has_episodes} -> {has_episodes}"
                    )
                    self.db.update_has_episodes(str(target_path), has_episodes)

            if cached_has_file is None or cached_has_file != has_file:
                if has_file is not None:
                    self.logger.debug(
                        f"Updating 'has_file' for {target_path}: {cached_has_file} -> {has_file}"
                    )
                    self.db.update_has_file(str(target_path), has_file)

            if cached_status is None or cached_status != status:
                if status is not None:
                    self.logger.debug(
                        f"Updating 'status' for {target_path}: {cached_status} -> {status}"
                    )
                    self.db.update_status(str(target_path), status)
            if cached_instance is None or cached_instance != instance:
                if instance is not None:
                    self.logger.debug(
                        f"Updating 'instance' for {target_path}: {cached_instance} -> {instance}"
                    )
                    self.db.update_instance(str(target_path), instance)
            if cached_arr_id is None or cached_arr_id != arr_id:
                if arr_id is not None:
                    self.logger.debug(
                        f"Updating 'arr_id' for {target_path}: {cached_arr_id} -> {arr_id}"
                    )
                    self.db.update_arr_id(str(target_path), arr_id)
            if cached_tmdb_id is None or cached_tmdb_id != tmdb_id:
                if tmdb_id is not None:
                    self.logger.debug(
                        f"Updating 'tmdb_id' for {target_path}: {cached_tmdb_id} -> {tmdb_id}"
                    )
                    self.db.update_tmdb_id(str(target_path), tmdb_id)
            if cached_imdb_id is None or cached_imdb_id != imdb_id:
                if imdb_id is not None:
                    self.logger.debug(
                        f"Updating 'imdb_id' for {target_path}: {cached_imdb_id} -> {imdb_id}"
                    )
                    self.db.update_imdb_id(str(target_path), imdb_id)
            if cached_tvdb_id is None or cached_tvdb_id != tvdb_id:
                if tvdb_id is not None:
                    self.logger.debug(
                        f"Updating 'tvdb_id' for {target_path}: {cached_tvdb_id} -> {tvdb_id}"
                    )
                    self.db.update_tvdb_id(str(target_path), tvdb_id)
            if (
                cached_file
                and cached_file["file_path"] == str(target_path)
                and cached_original_hash == original_file_hash
                and cached_source == current_source
                and cached_border_state == replace_border
                and cached_border_setting == self.border_setting
                and cached_custom_color == self.custom_color
            ):
                self.logger.debug(f"⏩ Skipping unchanged file: {file_path}")
                if webhook_run:
                    self.db.update_webhook_flag(str(target_path), True)
                return

        if not backup_dir:
            backup_dir = self.backup_dir
        try:
            if not backup_path.exists():
                shutil.copy2(file_path, backup_path)
                self.logger.debug(
                    f"Created backup of file {file_path} in {backup_dir}: {file_path}"
                )
            else:
                backed_up_hash = utils.hash_file(backup_path, self.logger)
                if original_file_hash != backed_up_hash:
                    shutil.copy2(file_path, backup_path)
                    self.logger.debug(
                        f"Updated backup at {backup_path}. Previous hash: {backed_up_hash}, New hash: {original_file_hash}"
                    )
                else:
                    self.logger.debug("Backup hashes match; no update needed")
        except Exception as e:
            self.logger.error(f"Error copying backup file {file_path}: {e}")

        if replace_border and self.border_setting:
            try:
                if self.border_setting.lower() == "remove":
                    final_image = self.border_replacerr.remove_border(file_path)
                    self.logger.info(f"Removed border on {file_path.name}")
                elif self.border_setting.lower() in {"custom", "black"}:
                    final_image = self.border_replacerr.replace_border(file_path)
                    self.logger.info(f"Replaced border on {file_path.name}")
                else:
                    self.logger.error(
                        f"Unsupported border setting: {self.border_setting}"
                    )
                    return

                temp_path = target_dir / f"temp_{new_file_name}"
                final_image.save(temp_path)
                file_path = temp_path
                file_hash = utils.hash_file(file_path, self.logger)
            except Exception as e:
                self.logger.error(f"Error processing border for {file_path}: {e}")
                file_hash = original_file_hash
        else:
            file_hash = original_file_hash
            if (
                target_path.exists()
                and cached_file
                and cached_file.get("border_replaced", False)
            ):
                try:
                    target_path.unlink()
                    self.logger.info(f"Deleted border-replaced file: {target_path}")
                except Exception as e:
                    self.logger.error(
                        f"Error deleting border-replaced file {target_path}: {e}"
                    )

        try:
            shutil.copy2(file_path, target_path)
            self.logger.info(f"Copied and renamed: {file_path} -> {target_path}")
            if cached_file:
                self.db.update_file(
                    file_hash=file_hash,
                    original_file_hash=original_file_hash,
                    source_path=current_source,
                    file_path=str(target_path),
                    border_replaced=replace_border,
                    border_setting=self.border_setting,
                    custom_color=self.custom_color,
                )
                self.logger.debug(f"Replaced cached file: {cached_file} -> {file_path}")
                if webhook_run:
                    self.db.update_webhook_flag(str(target_path), True)
            else:
                self.db.add_file(
                    file_path=str(target_path),
                    file_name=file_name_without_extension,
                    status=status,
                    has_episodes=has_episodes,
                    has_file=has_file,
                    media_type=media_type,
                    file_hash=file_hash,
                    original_file_hash=original_file_hash,
                    source_path=current_source,
                    border_replaced=replace_border,
                    border_setting=self.border_setting,
                    custom_color=self.custom_color,
                    webhook_run=webhook_run,
                    instance=instance,
                    arr_id=arr_id,
                    tmdb_id=tmdb_id,
                    imdb_id=imdb_id,
                    tvdb_id=tvdb_id,
                )
                self.logger.debug(f"Adding new file to database cache: {target_path}")
        except Exception as e:
            self.logger.error(f"Error copying file {file_path}: {e}")

        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    def setup_dirs(
        self,
        asset_type,
        media_name,
        file_path,
        season_special="",
        separator="",
    ):
        self.log_matched_file(asset_type, media_name, str(file_path), season_special)
        target_dir = None
        backup_dir = None
        file_name_format = None
        if file_path.exists() and file_path.is_file():
            if self.asset_folders:
                target_dir = self.target_path / sanitize_filename(media_name)
                backup_dir = self.backup_dir / sanitize_filename(media_name)
                file_prefix = season_special if not season_special == "" else "poster"
                file_name_format = f"{file_prefix}{file_path.suffix}"
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Created directory -> '{target_dir}'")
                if not backup_dir.exists():
                    backup_dir.mkdir(parents=True, exist_ok=True)

            else:
                backup_dir = None
                target_dir = self.target_path
                file_name_format = sanitize_filename(
                    f"{media_name}{separator}{season_special}{file_path.suffix}"
                )
        return target_dir, backup_dir, file_name_format

    def copy_rename_files(
        self,
        matched_files: dict[str, dict],
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
        webhook_run: bool | None = None,
    ) -> None:
        matched_movies = len(matched_files.get("movies", []))
        matched_shows = len(matched_files.get("shows", []))
        matched_collections = len(matched_files.get("collections", []))
        total_matched_items = matched_movies + matched_shows + matched_collections
        with tqdm(
            total=total_matched_items,
            desc=f"Processing matched files (webhook_run={webhook_run})",
        ) as progress_bar:
            processed_items = 0
            for key, items in matched_files.items():
                if key == "movies":
                    for file_path, data in items.items():
                        movie_data = data["match"]
                        movie_title = movie_data["title"]
                        movie_folder = movie_data["folder"]
                        target_dir, backup_dir, file_name_format = self.setup_dirs(
                            "movie", movie_folder, file_path
                        )
                        if target_dir and file_name_format:
                            self._copy_file(
                                file_path,
                                key,
                                target_dir,
                                backup_dir,
                                file_name_format,
                                self.replace_border,
                                status=data.get("status", None),
                                has_file=data.get("has_file", None),
                                webhook_run=webhook_run,
                                arr_id=movie_data.get("id"),
                                instance=movie_data.get("instance"),
                                imdb_id=movie_data.get("imdb_id", None),
                                tmdb_id=movie_data.get("tmdb_id", None),
                            )
                        else:
                            self.logger.warning(
                                f"Target dir: '{target_dir}' or file_name_format: '{file_name_format}' missing for item '{movie_title}'. Skipping.."
                            )
                            continue
                        processed_items += 1
                        progress_bar.update(1)
                        if job_id and cb:
                            progress = int((processed_items / total_matched_items) * 10)
                            cb(job_id, 80 + progress, ProgressState.IN_PROGRESS)

                if key == "collections":
                    for item in items:
                        file_path = item["file"]
                        collection = item["match"]
                        target_dir, backup_dir, file_name_format = self.setup_dirs(
                            "collection", collection, file_path
                        )

                        if target_dir and file_name_format:
                            self._copy_file(
                                file_path,
                                key,
                                target_dir,
                                backup_dir,
                                file_name_format,
                                self.replace_border,
                                webhook_run=webhook_run,
                            )
                        else:
                            self.logger.warning(
                                f"Target dir: '{target_dir}' or file_name_format: '{file_name_format}' missing for item '{collection}'. Skipping.."
                            )
                            continue
                        processed_items += 1
                        progress_bar.update(1)
                        if job_id and cb:
                            progress = int((processed_items / total_matched_items) * 10)
                            cb(job_id, 80 + progress, ProgressState.IN_PROGRESS)

                if key == "shows":
                    for file_path, data in items.items():
                        show_data = data["match"]
                        show_name = show_data["title"]
                        show_folder = show_data["folder"]

                        match_season = re.match(r"(.+?) - Season (\d+)", file_path.stem)
                        match_specials = re.match(r"(.+?) - Specials", file_path.stem)

                        if match_season:
                            season_num = int(match_season.group(2))
                            formatted_season_num = f"Season{season_num:02}"
                            target_dir, backup_dir, file_name_format = self.setup_dirs(
                                "season",
                                show_folder,
                                file_path,
                                formatted_season_num,
                                "_",
                            )
                        elif match_specials:
                            target_dir, backup_dir, file_name_format = self.setup_dirs(
                                "special",
                                show_folder,
                                file_path,
                                "Season00",
                                "_",
                            )
                        else:
                            target_dir, backup_dir, file_name_format = self.setup_dirs(
                                "series", show_folder, file_path
                            )

                        if target_dir and file_name_format:
                            self._copy_file(
                                file_path,
                                key,
                                target_dir,
                                backup_dir,
                                file_name_format,
                                self.replace_border,
                                status=data.get("status", None),
                                has_episodes=data.get("has_episodes", None),
                                webhook_run=webhook_run,
                                arr_id=show_data.get("id"),
                                instance=show_data.get("instance"),
                                imdb_id=show_data.get("imdb_id", None),
                                tmdb_id=show_data.get("tmdb_id", None),
                                tvdb_id=show_data.get("tvdb_id", None),
                            )
                        else:
                            self.logger.warning(
                                f"Target dir: '{target_dir}' or file_name_format: '{file_name_format}' missing for item '{show_name}'. Skipping.."
                            )
                            continue
                        processed_items += 1
                        progress_bar.update(1)
                        if job_id and cb:
                            progress = int((processed_items / total_matched_items) * 10)
                            cb(job_id, 80 + progress, ProgressState.IN_PROGRESS)

    def handle_single_item(
        self,
        asset_type: str,
        instances: dict,
        single_item: dict,
        upload_to_plex: bool,
    ) -> dict[str, list] | None:
        media_dict = {"movies": [], "shows": []}
        instance_name = single_item.get("instance_name", "").lower()
        item_id = single_item.get("item_id")
        if not instance_name:
            self.logger.error("Instance name is missing for movie item")
            return None
        if not item_id or not isinstance(item_id, int):
            self.logger.error(
                f"Invalid item ID: {item_id} for instance: {instance_name}"
            )
            return None
        normalized_instances = {key.lower(): value for key, value in instances.items()}
        arr_instance = normalized_instances.get(instance_name)
        if not arr_instance:
            self.logger.error(f"Arr instance '{instance_name}' not found")
            return None
        try:
            items = (
                arr_instance.get_movie(item_id)
                if asset_type == "movie"
                else arr_instance.get_show(item_id)
            )
            if not items:
                self.logger.error(
                    f"{asset_type.capitalize()} with ID {item_id} not found in instance {instance_name}"
                )
                return None

            for item in items:
                media_dict["movies" if asset_type == "movie" else "shows"].append(item)
            self.logger.debug(f"Fetched {asset_type}: {items}")
            return media_dict

        except Exception as e:
            self.logger.error(
                f"Error fetching {asset_type} from instance {instance_name}: {e}",
                exc_info=True,
            )
            return None

    def run(
        self,
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
        single_item: dict | None = None,
    ) -> dict | None:
        from modules import utils

        try:
            unmatched_media_dict = {}
            unmatched_collections_dict = {}
            media_dict = {}
            collections_dict = {}
            self._log_banner(job_id)
            if single_item:
                self.logger.info("Run triggered for a single item via webhook")
                asset_type = single_item.get("type", "")
                combined_instances_dict = self.radarr_instances | self.sonarr_instances
                collections_dict = {"movies": [], "shows": []}

                media_dict = self.handle_single_item(
                    asset_type,
                    combined_instances_dict,
                    single_item,
                    self.upload_to_plex,
                )
                if not media_dict:
                    self.logger.error(
                        "Failed to create media dictionary for single item.. Exiting."
                    )
                    if job_id and cb:
                        cb(job_id, 95, ProgressState.IN_PROGRESS)
                    return
            else:
                if self.only_unmatched and not single_item:
                    self.logger.debug(
                        "Creating media and collections dict of unmatched items in library"
                    )
                    unmatched_media_dict = self.get_unmatched_media_dict()
                    unmatched_collections_dict = self.get_unmatched_collections_dict()
                else:
                    self.logger.debug(
                        "Creating media and collections dict of all items in library"
                    )

                media_dict = utils.get_combined_media_dict(
                    self.radarr_instances, self.sonarr_instances, self.logger
                )
                collections_dict = utils.get_combined_collections_dict(
                    self.plex_instances
                )

            effective_media_dict = (
                unmatched_media_dict
                if self.only_unmatched and not single_item
                else media_dict
            )
            effective_collections_dict = (
                unmatched_collections_dict
                if self.only_unmatched and not single_item
                else collections_dict
            )

            if not any(effective_media_dict.values()) and not any(
                effective_collections_dict.values()
            ):
                self.logger.warning(
                    "Media and collections dictionaries are empty. Skipping processing."
                )
                if self.clean_assets:
                    self.logger.info(f"Cleaning orphan assets in {self.target_path}")
                    self.clean_asset_dir(media_dict, collections_dict)
                self.logger.info("Cleaning cache.")
                self.clean_cache()
                self.logger.info("Done.")
                if job_id and cb:
                    cb(job_id, 95, ProgressState.IN_PROGRESS)
                return

            self.logger.debug(
                "Media dict summary:\n%s", json.dumps(effective_media_dict, indent=4)
            )
            self.logger.debug(
                "Collections dict summary:\n%s",
                json.dumps(effective_collections_dict, indent=4),
            )

            if job_id and cb:
                cb(job_id, 10, ProgressState.IN_PROGRESS)
            source_files = self.get_source_files()
            self.logger.debug("Matching files with media")
            matched_files = self.match_files_with_media(
                source_files,
                effective_media_dict,
                effective_collections_dict,
                cb,
                job_id,
            )
            if self.asset_folders:
                self.logger.debug(
                    "-------------------------------------------------------"
                )
                self.logger.debug(f"Asset Folders: {self.asset_folders}")
                self.logger.debug("Starting file copying and renaming")
            else:
                self.logger.debug(
                    "-------------------------------------------------------"
                )
                self.logger.debug(f"Asset Folders: {self.asset_folders}")
                self.logger.debug("Starting file copying and renaming")

            self.copy_rename_files(
                matched_files,
                cb,
                job_id,
                webhook_run=bool(single_item),
            )

            if self.clean_assets and not single_item:
                self.logger.info(f"Cleaning orphan assets in {self.target_path}")
                self.clean_asset_dir(media_dict, collections_dict)
            self.logger.info("Cleaning cache.")
            self.clean_cache()
            self.logger.info("Done.")
            if job_id and cb:
                cb(job_id, 95, ProgressState.IN_PROGRESS)
            if single_item:
                return media_dict
        except Exception as e:
            self.logger.critical(f"Unexpected error occurred: {e}", exc_info=True)
            raise
