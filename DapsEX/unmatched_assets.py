import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from tabulate import tabulate

from DapsEX import utils
from DapsEX.database_cache import Database
from DapsEX.logger import init_logger
from DapsEX.media import Radarr, Server, Sonarr
from DapsEX.settings import Settings
from DapsEX.utils import remove_chars
from Payloads.unmatched_assets_payload import Payload
from progress import ProgressState


class UnmatchedAssets:
    def __init__(self, payload: Payload):
        self.logger = logging.getLogger("UnmatchedAssets")
        try:
            log_dir = Path(Settings.LOG_DIR.value) / Settings.UNMATCHED_ASSETS.value
            init_logger(
                self.logger,
                log_dir,
                "unmatched_assets",
                log_level=payload.log_level if payload.log_level else logging.INFO,
            )
            self.assets_dir = Path(payload.target_path)
            self.asset_folders = payload.asset_folders
            self.show_all_unmatched = payload.show_all_unmatched
            self.radarr_instances, self.sonarr_instances = utils.create_arr_instances(
                payload, Radarr, Sonarr, self.logger
            )
            self.plex_instances = utils.create_plex_instances(
                payload, Server, self.logger
            )
            self.db = Database(self.logger)
            self.db.initialize_stats()
        except Exception as e:
            self.logger.exception("Failed to initialize UnmatchedAssets")
            raise e

    image_exts = {".png", ".jpg", ".jpeg"}

    def _log_banner(self, job_id):
        self.logger.info("\n" + "#" * 80)
        self.logger.info(f"### New UnmatchedAssets Run -- Job ID: '{job_id}'")
        self.logger.info("\n" + "#" * 80)

    def get_assets_from_db(self):
        return self.db.return_all_files()

    def extract_assets(
        self,
        asset_type,
        asset_dict,
        is_series_asset: bool | None = None,
        is_collection_asset: bool | None = None,
    ) -> list | list[tuple[str, str]]:
        extracted_assets = []
        season_pattern = r"Season\d+"
        for asset_path, data in asset_dict.items():
            if data.get("media_type") != asset_type:
                continue
            if self.asset_folders:
                asset_name = (
                    remove_chars(Path(asset_path).parent.name)
                    if is_collection_asset
                    else Path(asset_path).parent.name.lower()
                )
            else:
                asset_name = (
                    remove_chars(data.get("file_name"))
                    if is_collection_asset
                    else data.get("file_name").lower()
                )

            season_match = re.search(
                season_pattern, data.get("file_name"), re.IGNORECASE
            )
            if is_series_asset and asset_type == "shows":
                if season_match:
                    if self.asset_folders:
                        extracted_assets.append(
                            (
                                Path(asset_path).parent.name.lower(),
                                season_match.group().lower(),
                            )
                        )
                    else:
                        asset_match = re.match(r"^(.*?)_(.*)$", asset_name)
                        if asset_match:
                            name, season = asset_match.groups()
                            extracted_assets.append((name, season))
            else:
                if not season_match:
                    extracted_assets.append(asset_name)

        return extracted_assets

    # need to update this function to be aligned with the matching... really need a common function
    # that takes in raw asset and raw media and "does magic" in both places... but not so simple...
    # removing prefixes, spaces, and (us) etc breaks here...
    def get_unmatched_assets(
        self,
        media_dict: dict[str, list[dict]],
        collections_dict: dict[str, list[str]],
        assets: dict,
        show_all_unmatched: bool,
    ) -> dict[str, list]:
        unmatched_assets = {"movies": [], "collections": [], "shows": []}

        movies_list_dict = media_dict.get("movies", [])
        shows_list_dict = media_dict.get("shows", [])
        movie_assets = self.extract_assets("movies", assets)
        show_assets = self.extract_assets("shows", assets)
        collection_assets = self.extract_assets(
            "collections", assets, is_collection_asset=True
        )
        season_assets = self.extract_assets("shows", assets, is_series_asset=True)

        for movie in movies_list_dict:
            if movie["folder"].lower() not in movie_assets:
                if show_all_unmatched:
                    unmatched_assets["movies"].append(utils.strip_id(movie["title"]))
                    self.db.add_unmatched_movie(
                        title=utils.strip_id(movie["title"]),
                        arr_id=movie["id"],
                        instance=movie["instance"],
                    )
                elif movie.get("has_file", False):
                    unmatched_assets["movies"].append(utils.strip_id(movie["title"]))
                    self.db.add_unmatched_movie(
                        title=utils.strip_id(movie["title"]),
                        arr_id=movie["id"],
                        instance=movie["instance"],
                    )
                else:
                    self.logger.debug(f"Skipping {movie['title']} -> No file on disk")

        for _, value_list in collections_dict.items():
            for collection in value_list:
                collection_clean = collection.replace("/", "")
                collection_clean = remove_chars(collection_clean)
                if collection_clean not in collection_assets:
                    unmatched_assets["collections"].append(collection)
                    self.db.add_unmatched_collection(title=collection)

        for item in shows_list_dict:
            show_title = utils.strip_id(item["title"])
            unmatched_show = {
                "title": show_title,
                "seasons": [],
                "main_poster_missing": False,
            }

            show_id = None
            if item["folder"].lower() not in show_assets:
                if show_all_unmatched or item.get("has_episodes", False):
                    show_id = self.db.add_unmatched_show(
                        title=show_title,
                        arr_id=item["id"],
                        main_poster_missing=True,
                        instance=item["instance"],
                    )
                    unmatched_show["main_poster_missing"] = True
                else:
                    self.logger.debug(f"Skipping {item['title']} -> No file on disk")

            for season in item.get("seasons", []):
                season_name = item["folder"].lower()
                season_number = season["season"]
                season_asset = (season_name, season_number)

                if self.asset_folders:
                    if season_asset not in season_assets:
                        if show_all_unmatched or season.get("has_episodes", False):
                            unmatched_show["seasons"].append(season["season"])
                            if show_id is None:
                                series_parent_path = self.assets_dir / item["folder"]
                                main_series_poster = None
                                for ext in self.image_exts:
                                    potential_poster = (
                                        series_parent_path / f"poster{ext}"
                                    )
                                    if potential_poster.exists():
                                        main_series_poster = potential_poster
                                        break
                                if main_series_poster is None:
                                    show_id = self.db.add_unmatched_show(
                                        title=show_title,
                                        arr_id=item["id"],
                                        main_poster_missing=True,
                                        instance=item["instance"],
                                    )
                                    unmatched_show["main_poster_missing"] = True
                                else:
                                    show_id = self.db.add_unmatched_show(
                                        title=show_title,
                                        arr_id=item["id"],
                                        main_poster_missing=False,
                                        instance=item["instance"],
                                    )
                            if show_id is None:
                                self.logger.error(
                                    f"Failed to assign a valid show_id for {show_title}"
                                )
                                continue

                            self.db.add_unmatched_season(
                                show_id=show_id, season=season["season"]
                            )
                        else:
                            self.logger.debug(
                                f"Skipping {utils.strip_id(item['title'])} - {season['season']} -> No episodes on disk"
                            )
                else:
                    if season_asset not in season_assets:
                        if show_all_unmatched or season.get("has_episodes", False):
                            unmatched_show["seasons"].append(season["season"])
                            if show_id is None:
                                show_id = self.db.add_unmatched_show(
                                    title=show_title,
                                    arr_id=item["id"],
                                    main_poster_missing=False,
                                    instance=item["instance"],
                                )
                            self.db.add_unmatched_season(
                                show_id=show_id, season=season["season"]
                            )
                        else:
                            self.logger.debug(
                                f"Skipping {utils.strip_id(item['title'])} - {season['season']} -> No episodes on disk"
                            )

            if unmatched_show["seasons"] or unmatched_show["main_poster_missing"]:
                unmatched_assets["shows"].append(unmatched_show)

        return unmatched_assets

    def cleanup_unmatched_media(self, new_unmatched_assets: dict[str, list]):
        current_unmatched_assets = self.db.get_all_unmatched_assets()

        self._cleanup_unmatched_movies(
            new_unmatched_assets["movies"], current_unmatched_assets["movies"]
        )
        self._cleanup_unmatched_collections(
            new_unmatched_assets["collections"], current_unmatched_assets["collections"]
        )
        self._cleanup_unmatched_show_seasons(
            new_unmatched_assets["shows"], current_unmatched_assets["shows"]
        )

    def _cleanup_unmatched_movies(
        self, new_unmatched_movies: list[str], current_unmatched_movies: list[dict]
    ):
        for movie in current_unmatched_movies:
            if movie["title"] not in new_unmatched_movies:
                self.db.delete_unmatched_asset(
                    db_table="unmatched_movies", title=movie["title"]
                )
                self.logger.debug(
                    f"Removed movie: {movie['title']} from unmatched database"
                )

    def _cleanup_unmatched_collections(
        self,
        new_unmatched_collections: list[str],
        current_unmatched_collections: list[dict],
    ):
        for collection in current_unmatched_collections:
            if collection["title"] not in new_unmatched_collections:
                self.db.delete_unmatched_asset(
                    db_table="unmatched_collections", title=collection["title"]
                )
                self.logger.debug(
                    f"Removed collection: {collection['title']} from unmatched database"
                )

    def _cleanup_unmatched_show_seasons(
        self, new_unmatched_shows: list[dict], current_unmatched_shows: list[dict]
    ):
        new_unmatched_lookup = {show["title"]: show for show in new_unmatched_shows}
        for show in current_unmatched_shows:
            show_title = show["title"]
            if show_title not in new_unmatched_lookup:
                self.db.delete_unmatched_asset(
                    db_table="unmatched_shows", title=show_title
                )
                self.logger.debug(f"Removed show: {show_title} from unmatched database")
                continue

            new_unmatched_show = new_unmatched_lookup[show_title]
            new_unmatched_seasons = set(new_unmatched_show.get("seasons", []))
            current_unmatched_seasons = set(show.get("seasons", []))
            seasons_to_delete = current_unmatched_seasons - new_unmatched_seasons

            for season in seasons_to_delete:
                self.db.delete_unmatched_season(show_id=show["id"], season=season)
                self.logger.debug(
                    f"Removed season: {season} for {show_title} from unmatched database"
                )

    def get_unmatched_count_dict(
        self,
        unmatched_assets: dict[str, list],
        media_dict: dict[str, list[dict]],
        collections_dict: dict[str, list[str]],
        show_all_unmatched: bool,
    ):
        asset_count_dict = {
            "total_movies": 0,
            "total_series": 0,
            "total_seasons": 0,
            "total_collections": 0,
            "unmatched_movies": 0,
            "unmatched_series": 0,
            "unmatched_seasons": 0,
            "unmatched_collections": 0,
        }

        shows_list = media_dict.get("shows", [])
        movies_list = media_dict.get("movies", [])

        if show_all_unmatched:
            total_movies = len(movies_list)
            total_shows = len(shows_list)
            total_seasons = sum(len(show.get("seasons", [])) for show in shows_list)
        else:
            total_movies = sum(
                1 for movie in movies_list if movie.get("has_file", False)
            )
            total_shows = sum(
                1 for show in shows_list if show.get("has_episodes", False)
            )
            total_seasons = sum(
                sum(
                    1
                    for season in show.get("seasons", [])
                    if season.get("has_episodes", False)
                )
                for show in shows_list
            )

        total_collections = sum(
            len(collections_dict.get(key, [])) for key in ["movies", "shows"]
        )

        asset_count_dict["total_movies"] = total_movies
        asset_count_dict["total_series"] = total_shows
        asset_count_dict["total_seasons"] = total_seasons
        asset_count_dict["total_collections"] = total_collections

        unmatched_show_season_list = unmatched_assets.get("shows", [])
        unmatched_show_list = [
            show
            for show in unmatched_show_season_list
            if show.get("main_poster_missing", True)
        ]
        unmatched_movie_list = unmatched_assets.get("movies", [])
        unmatched_collection_list = unmatched_assets.get("collections", [])
        asset_count_dict["unmatched_movies"] = len(unmatched_movie_list)
        asset_count_dict["unmatched_collections"] = len(unmatched_collection_list)
        asset_count_dict["unmatched_series"] = len(unmatched_show_list)
        asset_count_dict["unmatched_seasons"] = sum(
            len(show.get("seasons", [])) for show in unmatched_show_season_list
        )

        self.db.update_stats(asset_count_dict)
        return asset_count_dict

    def print_output(
        self,
        asset_count_dict: dict[str, int],
        unmatched_assets: dict[str, list],
    ) -> None:
        total_movies = asset_count_dict.get("total_movies", 0)
        total_shows = asset_count_dict.get("total_series", 0)
        total_seasons = asset_count_dict.get("total_seasons", 0)
        total_collections = asset_count_dict.get("total_collections", 0)
        grand_total = total_movies + total_shows + total_seasons + total_collections

        unmatched_movie_count = asset_count_dict.get("unmatched_movies", 0)
        unmatched_show_count = asset_count_dict.get("unmatched_series", 0)
        unmatched_season_count = asset_count_dict.get("unmatched_seasons", 0)
        unmatched_collection_count = asset_count_dict.get("unmatched_collections", 0)
        unmatched_grand_total = (
            unmatched_movie_count
            + unmatched_show_count
            + unmatched_season_count
            + unmatched_collection_count
        )

        percent_complete_movies = (
            100 * (total_movies - unmatched_movie_count) / total_movies
            if total_movies
            else 0
        )
        percent_complete_shows = (
            100 * (total_shows - unmatched_show_count) / total_shows
            if total_shows
            else 0
        )
        percent_complete_seasons = (
            100 * (total_seasons - unmatched_season_count) / total_seasons
            if total_seasons
            else 0
        )
        percent_complete_collections = (
            100 * (total_collections - unmatched_collection_count) / total_collections
            if total_collections
            else 0
        )
        percent_complete_grand_total = (
            100 * (grand_total - unmatched_grand_total) / grand_total
            if grand_total
            else 0
        )

        unmatched_movie_list = unmatched_assets.get("movies", [])
        unmatched_show_season_list = unmatched_assets.get("shows", [])
        unmatched_collection_list = unmatched_assets.get("collections", [])

        if unmatched_movie_list:
            table_data = [["UNMATCHED MOVIES", ""]]
            for movie in unmatched_movie_list:
                table_data.append([movie])
            self.logger.info(
                "\n" + tabulate(table_data, headers="firstrow", tablefmt="fancy_grid")
            )

        if unmatched_show_season_list:
            table_data = [["UNMATCHED SHOWS AND SEASONS", ""]]

            for show in unmatched_show_season_list:
                show_clean = utils.strip_id(show["title"])
                missing_assets = []
                if show.get("main_poster_missing", True):
                    missing_assets.append("show poster")
                missing_seasons = [season for season in show.get("seasons", [])]
                missing_assets.extend(missing_seasons)
                missing_assets_str = ", ".join(missing_assets) or "None"
                table_data.append([show_clean, missing_assets_str])

            self.logger.info(
                "\n" + tabulate(table_data, headers="firstrow", tablefmt="fancy_grid")
            )

        if unmatched_collection_list:
            table_data = [["UNMATCHED COLLECTIONS", ""]]
            for collection in unmatched_collection_list:
                table_data.append([collection])
            self.logger.info(
                "\n" + tabulate(table_data, headers="firstrow", tablefmt="fancy_grid")
            )

        total_table_data = [
            [
                "Movies",
                total_movies,
                unmatched_movie_count,
                f"{percent_complete_movies:.2f}%",
            ],
            [
                "Series",
                total_shows,
                unmatched_show_count,
                f"{percent_complete_shows:.2f}%",
            ],
            [
                "Seasons",
                total_seasons,
                unmatched_season_count,
                f"{percent_complete_seasons:.2f}%",
            ],
            [
                "Collections",
                total_collections,
                unmatched_collection_count,
                f"{percent_complete_collections:.2f}%",
            ],
            [
                "Grand Total",
                grand_total,
                unmatched_grand_total,
                f"{percent_complete_grand_total:.2f}%",
            ],
        ]
        self.logger.info(
            "\n"
            + tabulate(
                total_table_data,
                headers=["Type", "Total", "Unmatched", "Percent Complete"],
                tablefmt="fancy_grid",
            )
        )

    def run(
        self,
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
    ):
        from DapsEX import utils

        try:
            self._log_banner(job_id)
            if job_id and cb:
                cb(job_id, 20, ProgressState.IN_PROGRESS)

            self.logger.debug("Creating media and collections dict.")
            media_dict = utils.get_combined_media_dict(
                self.radarr_instances, self.sonarr_instances, self.logger
            )
            collections_dict = utils.get_combined_collections_dict(self.plex_instances)
            if job_id and cb:
                cb(job_id, 30, ProgressState.IN_PROGRESS)
            self.logger.debug("Created media dict and collections dict")
            self.logger.debug("Getting all assets")
            assets = self.db.return_all_files()
            if job_id and cb:
                cb(job_id, 50, ProgressState.IN_PROGRESS)

            self.logger.debug("Getting all unmatched assets and asset counts")
            unmatched_assets = self.get_unmatched_assets(
                media_dict,
                collections_dict,
                assets,
                self.show_all_unmatched,
            )
            self.logger.debug(
                "Unmatched assets summary:\n%s", json.dumps(unmatched_assets, indent=4)
            )
            asset_count_dict = self.get_unmatched_count_dict(
                unmatched_assets,
                media_dict,
                collections_dict,
                self.show_all_unmatched,
            )
            if job_id and cb:
                cb(job_id, 70, ProgressState.IN_PROGRESS)
            self.logger.debug("Cleaning up database")

            self.cleanup_unmatched_media(unmatched_assets)
            self.print_output(asset_count_dict, unmatched_assets)
            if job_id and cb:
                cb(job_id, 100, ProgressState.COMPLETED)
        except Exception as e:
            self.logger.exception("Failed to run UnmatchedAssets")
            if job_id and cb:
                cb(job_id, 100, ProgressState.COMPLETED)
            raise e
