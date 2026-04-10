import json
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path

from modules import utils
from modules.database_cache import Database
from modules.logger import init_logger
from modules.media import Radarr, Server, Sonarr
from modules.settings import Settings
from progress import ProgressState


class PlexUploaderr:
    DEFAULT_EDITION_MOVIE = "postarr_edition"

    def __init__(
        self,
        payload,
        webhook_item: dict | None = None,
        media_dict: dict | None = None,
    ) -> None:
        from modules.settings import Settings

        self.logger = logging.getLogger(Settings.PLEX_UPLOADERR.value)
        try:
            log_dir = Path(Settings.LOG_DIR.value) / Settings.PLEX_UPLOADERR.value
            init_logger(
                self.logger,
                log_dir,
                Settings.PLEX_UPLOADERR.value,
                payload.log_level if payload.log_level else logging.INFO,
            )
            self.db = Database(self.logger)
            self.asset_folders = payload.asset_folders
            self.reapply_posters = payload.reapply_posters
            self.plex_instances = utils.create_plex_instances(
                payload, Server, self.logger
            )
            self.radarr_instances, self.sonarr_instances = utils.create_arr_instances(
                payload, Radarr, Sonarr, self.logger
            )
            self.webhook_item = webhook_item
            self.media_dict = media_dict
            self.webhook_initial_delay = payload.webhook_initial_delay
            self.webhook_retry_delay = payload.webhook_retry_delay
            self.webhook_max_retries = payload.webhook_max_retries
        except Exception as e:
            self.logger.error(
                "Failed to initialize plex-uploaderr: %s", e, exc_info=True
            )
            raise

    def add_poster_to_plex(
        self,
        plex_media_objects: list,
        file_path: str,
        show_title: str | None = None,
    ):
        libraries = set()
        editions = set()
        for item in plex_media_objects:
            try:
                library = getattr(item, "librarySectionTitle", "Unknown Library")
                edition = self.get_edition_title_from_plex_object(item)
                labels = getattr(item, "labels", None)
                has_kometa_overlay_label = False
                if labels:
                    for label in labels:
                        if label.tag == "Overlay":
                            has_kometa_overlay_label = True
                            break
                item.uploadPoster(filepath=file_path)
                if has_kometa_overlay_label:
                    item.removeLabel(["Overlay"])
                    self.logger.debug(
                        "Removed kometa overlay for item '%s'", item.title
                    )
                libraries.add(library)
                if edition:
                    editions.add(edition)
                if show_title:
                    self.logger.info(
                        "Uploaded poster for show '%s' item '%s' to library '%s'",
                        show_title,
                        item.title,
                        library,
                    )
                else:
                    self.logger.info(
                        "Uploaded poster for item '%s' to library '%s'",
                        item.title,
                        library,
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to upload poster for item '%s': %s",
                    item.title,
                    e,
                    exc_info=True,
                )
        self.db.update_uploaded_to_libraries(file_path, list(libraries))
        if editions:
            self.db.update_uploaded_editions(file_path, list(editions))

    def process_items(
        self,
        processed_files: set,
        cached_items: dict,
        plex_dict: dict,
        item_type: str,
    ):
        try:
            for file_path, file_info in cached_items.items():
                if file_path in processed_files:
                    continue

                if self.asset_folders:
                    asset_file_path = Path(file_path)
                    file_name = utils.remove_chars(asset_file_path.parent.name)
                else:
                    file_name = utils.remove_chars(file_info["file_name"])

                self.logger.trace(  # type: ignore[attr-defined]
                    "Processing cached %s file: %s", item_type, file_path
                )
                uploaded_to_libraries = file_info.get("uploaded_to_libraries", [])
                uploaded_editions = file_info.get("uploaded_editions", [])
                item_matches = self.find_match(
                    file_name,
                    plex_dict[item_type],
                    uploaded_to_libraries,
                    uploaded_editions,
                    file_path,
                )
                if not item_matches:
                    self.logger.debug(
                        "Item %s not found in plex, no further processing for this item",
                        file_path,
                    )
                    processed_files.add(file_path)
                    continue

                for library_name, item in item_matches:
                    self.logger.debug(
                        "Match found for file: %s -> Plex %s '%s' in library '%s'",
                        file_path,
                        item_type,
                        item.title,
                        library_name,
                    )
                item_list = [match[-1] for match in item_matches]
                if file_path not in processed_files:
                    processed_files.add(file_path)
                    self.add_poster_to_plex(item_list, file_path)
        except Exception as e:
            self.logger.error("Unexpected error processing files: %s", e, exc_info=True)
            raise

    def process_season_files(
        self,
        processed_files: set,
        plex_show_dict: dict,
        file_path: str,
        file_info: dict,
    ) -> bool:
        if self.asset_folders:
            season_match = re.match(r"^Season(\d+)", file_info["file_name"])
        else:
            season_match = re.match(
                r"^(.*\s\(\d{4}\)\s.*)_Season(\d+).*$", file_info["file_name"]
            )
        if not season_match:
            return False

        if self.asset_folders:
            asset_file_path = Path(file_path)
            file_name = utils.remove_chars(asset_file_path.parent.name)
            season_num = int(season_match.group(1))
        else:
            file_name = utils.remove_chars(season_match.group(1))
            season_num = int(season_match.group(2))
        self.logger.trace("Processing cached season file: %s", file_path)  # type: ignore[attr-defined]
        uploaded_to_libraries = file_info.get("uploaded_to_libraries", [])
        uploaded_editions = file_info.get("uploaded_editions", [])
        show_matches = self.find_match(
            file_name,
            plex_show_dict["show"],
            uploaded_to_libraries,
            uploaded_editions,
            file_path,
        )

        if not show_matches:
            self.logger.debug(
                "All libraries skipped for season, no further processing."
            )
            processed_files.add(file_path)
            return True

        for library_name, show in show_matches:
            self.logger.debug(
                "Match found for file %s -> Plex show '%s' in library '%s'",
                file_path,
                show.title,
                library_name,
            )
        matching_seasons = [
            (show.title, season)
            for _, show in show_matches
            for season in show.seasons()
            if season.index == season_num
        ]

        if matching_seasons:
            first_show_title, first_season = matching_seasons[0]
            self.logger.debug(
                "Match found for Season %s for Show '%s'",
                first_season,
                first_show_title,
            )

            seasons_only = [season for _, season in matching_seasons]
            if file_path not in processed_files:
                processed_files.add(file_path)
                self.add_poster_to_plex(seasons_only, file_path, first_show_title)
        else:
            for library_name, show in show_matches:
                self.logger.debug(
                    "Season %s not found for show '%s' in library '%s'",
                    season_num,
                    show.title,
                    library_name,
                )
        return True

    def find_match(
        self,
        file_name: str,
        plex_items: dict,
        uploaded_to_libraries: list,
        uploaded_editions: list,
        file_path: str,
    ):
        matches = []
        for library_name, item_dict in plex_items.items():
            self.logger.trace("Looking for match in library '%s'", library_name)  # type: ignore[attr-defined]
            for title, plex_object in item_dict.items():
                item_name = utils.remove_chars(title)
                if isinstance(plex_object, list):
                    for item in plex_object:
                        if file_name == item_name:
                            if item.type == "movie":
                                edition_title = self.get_edition_title_from_plex_object(
                                    item
                                )
                                self.logger.trace(  # type: ignore[attr-defined]
                                    "Edition title for %s %s: '%s'",
                                    item.type,
                                    title,
                                    edition_title,
                                )

                                if edition_title in uploaded_editions:
                                    self.logger.trace(  # type: ignore[attr-defined]
                                        "Edition '%s' already uploaded to library '%s' for %s, skipping",
                                        edition_title,
                                        library_name,
                                        item_name,
                                    )
                                    continue
                                if self.add_default_edition_if_needed(
                                    uploaded_to_libraries,
                                    uploaded_editions,
                                    file_path,
                                    library_name,
                                    item_name,
                                    edition_title,
                                ):
                                    continue
                            else:
                                if library_name in uploaded_to_libraries:
                                    self.logger.debug(
                                        "File already uploaded to library '%s' for %s, skipping",
                                        library_name,
                                        item_name,
                                    )
                                    continue

                            self.logger.debug(
                                "Match found '%s': file:%s --> plex:%s",
                                library_name,
                                file_name,
                                item_name,
                            )
                            matches.append((library_name, item))
                else:
                    if file_name == item_name:
                        if plex_object.type == "movie":
                            edition_title = self.get_edition_title_from_plex_object(
                                plex_object
                            )
                            if edition_title in uploaded_editions:
                                self.logger.trace(  # type: ignore[attr-defined]
                                    "Edition '%s' already uploaded to library '%s' for %s, skipping",
                                    edition_title,
                                    library_name,
                                    item_name,
                                )
                                continue
                            if self.add_default_edition_if_needed(
                                uploaded_to_libraries,
                                uploaded_editions,
                                file_path,
                                library_name,
                                item_name,
                                edition_title,
                            ):
                                continue
                        else:
                            if library_name in uploaded_to_libraries:
                                self.logger.debug(
                                    "File already uploaded to library '%s' for %s, skipping",
                                    library_name,
                                    item_name,
                                )
                                continue
                        self.logger.debug(
                            "Match found '%s': file:%s --> plex:%s",
                            library_name,
                            file_name,
                            item_name,
                        )
                        matches.append((library_name, plex_object))
        return matches

    def get_edition_title_from_plex_object(self, plex_object):
        edition_title = getattr(plex_object, "editionTitle", None)
        if not edition_title and plex_object.type == "movie":
            edition_title = PlexUploaderr.DEFAULT_EDITION_MOVIE
        return edition_title

    def add_default_edition_if_needed(
        self,
        uploaded_to_libraries,
        uploaded_editions,
        file_path,
        library_name,
        item_name,
        edition_title,
    ):
        if (
            edition_title == PlexUploaderr.DEFAULT_EDITION_MOVIE
            and not uploaded_editions
            and library_name in uploaded_to_libraries
        ):
            self.logger.trace(  # type: ignore[attr-defined]
                "Default edition already uploaded to '%s' for '%s', appending to editions and skipping",
                library_name,
                item_name,
            )
            uploaded_editions.append(edition_title)
            self.db.update_uploaded_editions(file_path, uploaded_editions)
            return True

        return False

    def upload_poster(
        self,
        cached_files: dict,
        plex_movie_dict: dict | None = None,
        plex_show_dict: dict | None = None,
    ) -> None:
        def filter_cached_files_by_type(cached_files, media_type):
            filtered_files = {
                file_path: file_info
                for file_path, file_info in cached_files.items()
                if file_info.get("media_type") == media_type
            }
            return filtered_files if filtered_files else {}

        processed_files = set()
        movies_only = filter_cached_files_by_type(cached_files, "movies")
        collections_only = filter_cached_files_by_type(cached_files, "collections")
        shows_only = filter_cached_files_by_type(cached_files, "shows")
        combined_collections = {"collections": {}}

        if plex_movie_dict:
            for library_name, collections_dict in plex_movie_dict.get(
                "collections", {}
            ).items():
                if library_name not in combined_collections:
                    combined_collections["collections"][library_name] = {}
                combined_collections["collections"][library_name].update(
                    collections_dict
                )

        if plex_show_dict:
            for library_name, collections_dict in plex_show_dict.get(
                "collections", {}
            ).items():
                if library_name not in combined_collections:
                    combined_collections["collections"][library_name] = {}
                combined_collections["collections"][library_name].update(
                    collections_dict
                )
        self.logger.debug("Processing all plex movie items")
        if plex_movie_dict:
            self.process_items(
                processed_files,
                movies_only,
                plex_movie_dict,
                "movie",
            )
        self.logger.debug("Processing all plex show items")
        if plex_show_dict:
            for file_path, file_info in shows_only.items():
                if file_path in processed_files:
                    continue

                is_season = self.process_season_files(
                    processed_files,
                    plex_show_dict,
                    file_path,
                    file_info,
                )

                if not is_season and file_path not in processed_files:
                    self.process_items(
                        processed_files,
                        {file_path: file_info},
                        plex_show_dict,
                        "show",
                    )
        self.logger.debug("Processing all plex collection items")
        if combined_collections:
            self.process_items(
                processed_files,
                collections_only,
                combined_collections,
                "collections",
            )

    def convert_plex_titles(
        self,
        plex_movie_dict: dict | None = None,
        plex_show_dict: dict | None = None,
    ) -> tuple[dict, dict]:
        updated_movie_dict = {}
        updated_show_dict = {}

        if plex_show_dict:
            for library_title, show_dict in plex_show_dict.get("show", {}).items():
                updated_show_dict[library_title] = {}
                for plex_title, show in show_dict.items():
                    try:
                        first_season = show.seasons()[0]
                        first_episode = first_season.episodes()[0]
                        first_media = first_episode.media[0]
                        first_part = first_media.parts[0]
                        item_path = Path(first_part.file)
                        season_folder = item_path.parent
                        show_folder = season_folder.parent
                        if not re.search(
                            r"season\s*\d+|specials", season_folder.name, re.IGNORECASE
                        ):
                            self.logger.warning(
                                "Show '%s' in library '%s' may have incorrect folder structure. "
                                "Expected a season folder but got '%s' - check that files are nested under a season folder.",
                                plex_title,
                                library_title,
                                season_folder.name,
                            )
                            continue
                        new_title = show_folder.name
                        updated_show_dict[library_title][new_title] = show
                    except Exception as e:
                        self.logger.warning(
                            "Could not determine path for show: '%s' in library '%s'. Error: %s",
                            plex_title,
                            library_title,
                            e,
                        )

        if plex_movie_dict:
            for library_title, movie_dict in plex_movie_dict.get("movie", {}).items():
                updated_movie_dict[library_title] = {}
                for plex_title, movie in movie_dict.items():
                    try:
                        file_part = next(
                            (
                                part.file
                                for media in movie.media
                                for part in media.parts
                                if part.file
                            ),
                            None,
                        )
                        if not file_part:
                            raise ValueError(
                                f"No valid file part found for {movie.title}"
                            )
                        item_path = Path(file_part)
                        new_title = item_path.parent.name

                        if new_title not in updated_movie_dict[library_title]:
                            updated_movie_dict[library_title][new_title] = []
                        updated_movie_dict[library_title][new_title].append(movie)

                    except Exception as e:
                        self.logger.warning(
                            "Could not determine path for movie '%s' in library '%s'. Error: %s",
                            plex_title,
                            library_title,
                            e,
                        )

            for library_title, movies in updated_movie_dict.items():
                for title in list(movies.keys()):
                    if len(movies[title]) == 1:
                        movies[title] = movies[title][0]

        return updated_movie_dict, updated_show_dict

    def search_recently_added_for_items(
        self,
        media_type: str,
        media_title: str,
        webhook_cached_files: dict,
    ):
        max_retries = self.webhook_max_retries
        retry_delay = self.webhook_retry_delay
        initial_delay = self.webhook_initial_delay
        found_item = False
        plex_media_dict = {}
        filtered_movies = {media_type: {}, "collections": {}}
        if initial_delay:
            self.logger.info(
                "Waiting %s seconds before searching for recently added items",
                initial_delay,
            )
            time.sleep(initial_delay)
        for attempt in range(1, max_retries + 1):
            self.logger.info(
                "Attempt %s/%s: Searching recently added items", attempt, max_retries
            )
            for name, server in self.plex_instances.items():
                recently_added_dict = server.fetch_recently_added(media_type)
                if not recently_added_dict:
                    continue

                key = "all_movies" if media_type == "movie" else "all_shows"
                plex_media_dict[name] = {key: recently_added_dict}

                for server_name, item_dict in plex_media_dict.items():
                    movie_dict, show_dict = self.convert_plex_titles(
                        plex_movie_dict=(
                            item_dict[key] if media_type == "movie" else None
                        ),
                        plex_show_dict=(
                            item_dict[key] if media_type == "show" else None
                        ),
                    )
                    relevant_dict = movie_dict if media_type == "movie" else show_dict

                    for library_name, items in relevant_dict.items():
                        for item_title, item_obj in items.items():
                            if item_title == media_title:
                                found_item = True
                                filtered_movies[media_type].setdefault(
                                    library_name, {}
                                )[item_title] = item_obj
                                self.logger.info(
                                    "Found '%s' in library '%s'",
                                    item_title,
                                    library_name,
                                )

                    if found_item:
                        item_dict[key] = filtered_movies
                        self.logger.info(
                            "Uploading posters for Plex instance: '%s'", server_name
                        )
                        self.upload_poster(
                            webhook_cached_files,
                            plex_movie_dict=(
                                item_dict["all_movies"]
                                if media_type == "movie"
                                else None
                            ),
                            plex_show_dict=(
                                item_dict["all_shows"] if media_type == "show" else None
                            ),
                        )
                        break

                if found_item:
                    self.logger.info("Item found successfully. Exiting search.")
                    return

            if attempt < max_retries:
                self.logger.info("Item not found. Retrying in %s seconds.", retry_delay)
                time.sleep(retry_delay)
            else:
                self.logger.warning(
                    "Item '%s' not found after %s retries.",
                    media_title,
                    max_retries,
                )

    def upload_posters_full(
        self,
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
    ):
        plex_media_dict = {}

        utils.log_banner(self.logger, Settings.PLEX_UPLOADERR.value, job_id)
        if self.reapply_posters:
            self.db.clear_uploaded_to_libraries_and_editions()
            self.logger.info(
                "Reapply posters: %s, clearing uploaded libraries data",
                self.reapply_posters,
            )
        else:
            self.logger.debug(
                "Reapply posters: %s, leaving cached upload state intact",
                self.reapply_posters,
            )

        cached_files = self.db.return_all_files()
        self.logger.trace(  # type: ignore[attr-defined]
            "File cache dump:\n%s", json.dumps(cached_files, indent=2)
        )

        if job_id and cb:
            cb(job_id, 10, ProgressState.IN_PROGRESS)

        self.logger.debug(
            "Attempting to update current has_file and has_episodes values"
        )
        self.update_cached_files(cached_files)
        if job_id and cb:
            cb(job_id, 20, ProgressState.IN_PROGRESS)

        valid_files = {}
        for file_path, file_info in cached_files.items():
            if (
                file_info.get("has_episodes")
                or file_info.get("has_file")
                or file_info.get("media_type") == "collections"
            ):
                valid_files[file_path] = file_info
            else:
                self.logger.debug(
                    "Skipping %s: has_episodes=%s, has_file=%s, media_type=%s",
                    file_path,
                    file_info.get("has_episodes"),
                    file_info.get("has_file"),
                    file_info.get("media_type"),
                )
        if job_id and cb:
            cb(job_id, 40, ProgressState.IN_PROGRESS)

        if valid_files:
            self.logger.debug("Total cached files: %s", len(cached_files))
            self.logger.debug("Valid files to process: %s", len(valid_files))
            for name, server in self.plex_instances.items():
                try:
                    self.logger.debug("Fetching Plex data from instance '%s'", name)
                    plex_movie_dict, plex_show_dict = server.get_media()
                    plex_media_dict[name] = {
                        "all_movies": plex_movie_dict,
                        "all_shows": plex_show_dict,
                    }
                    self.logger.debug(
                        "Finished fetching Plex data from instance '%s'", name
                    )
                except Exception as e:
                    self.logger.error(
                        "Error retrieving media for Plex instance '%s': %s",
                        name,
                        e,
                        exc_info=True,
                    )
                    plex_media_dict[name] = {"all_movies": {}, "all_shows": {}}
                    raise

            summary = {
                lib: {title: list(media.keys()) for title, media in sections.items()}
                for lib, sections in plex_media_dict.items()
            }
            self.logger.trace(  # type: ignore[attr-defined]
                "Plex media dict structure:\n%s",
                utils.normalize(json.dumps(summary, indent=2)),
            )

            if job_id and cb:
                cb(job_id, 60, ProgressState.IN_PROGRESS)

            for server_name, item_dict in plex_media_dict.items():
                try:
                    self.logger.debug(
                        "Converting Plex titles from paths for '%s'", server_name
                    )
                    updated_movie_dict, updated_show_dict = self.convert_plex_titles(
                        item_dict["all_movies"], item_dict["all_shows"]
                    )
                    item_dict["all_movies"]["movie"] = updated_movie_dict
                    item_dict["all_shows"]["show"] = updated_show_dict
                except Exception as e:
                    self.logger.error(
                        "Error creating updated media dict: %s", e, exc_info=True
                    )  # type: ignore[attr-defined]

                utils.log_plex_media_summary(self.logger, item_dict)
                self.logger.info(
                    "Uploading posters for Plex instance: '%s'", server_name
                )

                if job_id and cb:
                    cb(job_id, 80, ProgressState.IN_PROGRESS)
                self.upload_poster(
                    valid_files,
                    item_dict["all_movies"],
                    item_dict["all_shows"],
                )
                if job_id and cb:
                    cb(job_id, 100, ProgressState.COMPLETED)
        else:
            self.logger.info("No new files to upload to Plex")
            if job_id and cb:
                cb(job_id, 100, ProgressState.COMPLETED)

        self.logger.info("Finished plex upload.")

    def update_cached_files(self, cached_files: dict):
        media_dict = utils.get_combined_media_dict(
            self.radarr_instances, self.sonarr_instances
        )
        movies_lookup = {
            movie["folder"].lower(): movie["has_file"]
            for movie in media_dict.get("movies", [])
        }

        shows_lookup = {}
        for show in media_dict.get("shows", []):
            show_title = show["folder"].lower()
            shows_lookup[show_title] = {
                "has_episodes": show.get("has_episodes", False),
                "seasons": {
                    season["season"].lower(): season.get("has_episodes", False)
                    for season in show.get("seasons", [])
                },
            }

        for file_path, cached_item in cached_files.items():
            if self.asset_folders:
                title = Path(file_path).parent.name.lower()
                season_pattern = re.match(r"(Season\d+)", cached_item["file_name"])
                season = season_pattern.group(1).lower() if season_pattern else None
            else:
                full_name = (cached_item.get("file_name") or "").lower()
                title_pattern = re.match(r"(.*)_season\d+$", full_name)
                title = title_pattern.group(1) if title_pattern else full_name
                season_pattern = re.match(r".*_(season\d+)$", full_name)
                season = season_pattern.group(1).lower() if season_pattern else None

            media_type = cached_item.get("media_type")

            if media_type == "collections":
                continue

            if media_type == "movies":
                cached_has_file = bool(cached_item.get("has_file", 0))
                if title in movies_lookup:
                    current_has_file = movies_lookup[title]
                    if current_has_file != cached_has_file:
                        cached_item["has_file"] = int(current_has_file)
                        self.db.remove_upload_data_for_file(file_path)
                        self.db.update_has_file(file_path, current_has_file)
                else:
                    self.logger.warning(
                        "Movie title: '%s' not found in movies lookup when processing %s.",
                        title,
                        file_path,
                    )

            if media_type == "shows":
                cached_has_episodes = bool(cached_item.get("has_episodes", 0))
                if title in shows_lookup:
                    lookup_entry = shows_lookup[title]
                    if season:
                        current_has_episodes = lookup_entry["seasons"].get(
                            season, False
                        )
                    else:
                        current_has_episodes = lookup_entry["has_episodes"]

                    if current_has_episodes != cached_has_episodes:
                        cached_item["has_episodes"] = int(current_has_episodes)
                        self.db.remove_upload_data_for_file(file_path)
                        self.db.update_has_episodes(file_path, current_has_episodes)
                else:
                    self.logger.warning(
                        "Show title '%s' not found in shows lookup when processing '%s'.",
                        title,
                        file_path,
                    )

    def upload_posters_webhook(
        self,
        job_id: str,
    ):
        utils.log_banner(
            self.logger, Settings.PLEX_UPLOADERR.value + " (webhook)", job_id
        )
        if self.reapply_posters:
            self.db.clear_uploaded_to_libraries_and_editions(webhook_run=True)
            self.logger.debug(
                "Reapply posters: %s, clearing upload data for webhook-run items and re-uploading them to Plex if they exist",
                self.reapply_posters,
            )
        else:
            self.logger.debug(
                "Reapply posters: %s, leaving cached upload state intact",
                self.reapply_posters,
            )

        if not self.webhook_item:
            self.logger.error("Webhook item data missing. Exiting.")
            return

        if not self.media_dict:
            self.logger.error("Media dict item data missing. Exiting.")
            return

        plex_media_dict = {}
        item_type = self.webhook_item.get("type")
        if item_type == "movie":
            item = next((item for item in self.media_dict.get("movies", [])))
        else:
            item_type = "show"
            item = next((item for item in self.media_dict.get("shows", [])))
        item_title = item["folder"]

        webhook_cached_files = self.db.return_all_files(webhook_run=True)
        self.logger.trace(  # type: ignore[attr-defined]
            "File cache dump:\n%s", json.dumps(webhook_cached_files, indent=2)
        )

        self.logger.debug(
            "Attempting to update current has_file and has_episodes values for webhook items"
        )
        self.update_cached_files(webhook_cached_files)

        self.logger.debug("Updating webhook flag")
        for file_path in webhook_cached_files.keys():
            self.db.update_webhook_flag(file_path)

        if webhook_cached_files:
            for name, server in self.plex_instances.items():
                try:
                    if item_type == "movie":
                        item_dict = server.get_media(single_movie=True)
                    else:
                        item_dict = server.get_media(single_series=True)
                    if item_dict:
                        if item_type == "movie":
                            plex_media_dict[name] = {"all_movies": item_dict}
                        else:
                            plex_media_dict[name] = {"all_shows": item_dict}
                except Exception as e:
                    self.logger.error(
                        "Error retrieving media for Plex instance '%s': %s",
                        name,
                        e,
                        exc_info=True,
                    )
                    plex_media_dict[name] = {}
                    raise

            for server_name, item_dict in plex_media_dict.items():
                self.logger.debug(
                    "Converting plex titles to paths for '%s'", server_name
                )
                found_item = False
                if item_type == "movie":
                    updated_movie_dict, _ = self.convert_plex_titles(
                        plex_movie_dict=item_dict["all_movies"],
                        plex_show_dict=None,
                    )
                    filtered_movies = {"movie": {}, "collections": {}}

                    utils.log_plex_media_summary_webhook(
                        self.logger, updated_movie_dict
                    )
                    for library_name, movies in updated_movie_dict.items():
                        for movie_title, movie_obj in movies.items():
                            if item_title == movie_title:
                                found_item = True
                                filtered_movies["movie"].setdefault(library_name, {})[
                                    movie_title
                                ] = movie_obj

                    if found_item:
                        item_dict["all_movies"] = filtered_movies
                        self.logger.info(
                            "Uploading posters for Plex instance: '%s'", server_name
                        )
                        self.upload_poster(
                            webhook_cached_files,
                            plex_movie_dict=item_dict["all_movies"],
                            plex_show_dict=None,
                        )
                        break
                    else:
                        self.search_recently_added_for_items(
                            "movie",
                            item_title,
                            webhook_cached_files,
                        )
                else:
                    _, updated_show_dict = self.convert_plex_titles(
                        plex_movie_dict=None,
                        plex_show_dict=item_dict["all_shows"],
                    )
                    filtered_shows = {"show": {}, "collections": {}}

                    utils.log_plex_media_summary_webhook(self.logger, updated_show_dict)

                    for library_name, shows in updated_show_dict.items():
                        for show_title, show_obj in shows.items():
                            if item_title == show_title:
                                found_item = True
                                filtered_shows["show"].setdefault(library_name, {})[
                                    show_title
                                ] = show_obj

                    if found_item:
                        item_dict["all_shows"] = filtered_shows
                        self.logger.info(
                            "Uploading posters for Plex instance: '%s'", server_name
                        )
                        self.upload_poster(
                            webhook_cached_files,
                            plex_movie_dict=None,
                            plex_show_dict=item_dict["all_shows"],
                        )
                        break
                    else:
                        self.search_recently_added_for_items(
                            "show",
                            item_title,
                            webhook_cached_files,
                        )
        self.logger.info("Finished plex upload (webhook)")
