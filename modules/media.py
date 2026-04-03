from logging import Logger
from pathlib import Path

import plexapi
from arrapi import RadarrAPI, SonarrAPI
from arrapi.apis.sonarr import Series
from arrapi.exceptions import ConnectionFailure
from arrapi.exceptions import Unauthorized as ArrApiUnauthorized
from arrapi.objs.reload import Movie
from plexapi import utils as plexutils
from plexapi.collection import LibrarySection
from plexapi.exceptions import BadRequest, UnknownType
from plexapi.exceptions import Unauthorized as PlexApiUnauthorized
from plexapi.server import PlexServer


class Media:
    def get_series_with_seasons(
        self, logger, all_series_objects: list[Series], instance_name: str
    ):
        titles_with_seasons = []
        for media_object in all_series_objects:
            dict_with_seasons = {
                "title": "",
                "id": None,
                "seasons": [],
                "status": "",
                "has_episodes": False,
                "alternate_titles": [],
                "instance": instance_name,
            }
            series_id = media_object.id
            path = Path(media_object.path)  # type: ignore
            title = media_object.title
            year = str(media_object.year)
            tvdb_id = str(media_object.tvdbId)
            imdb_id = str(media_object.imdbId)
            tmdb_id = "0"
            series_status = media_object.status
            season_object = media_object.seasons
            dict_with_seasons["arr_title"] = title
            dict_with_seasons["status"] = series_status
            dict_with_seasons["id"] = series_id
            dict_with_seasons["media_year"] = year
            dict_with_seasons["tvdb_id"] = tvdb_id
            dict_with_seasons["imdb_id"] = imdb_id
            dict_with_seasons["path"] = media_object.path
            dict_with_seasons["folder"] = path.name
            # ugly to access the protected member, but needed for full data to avoid extra API calls
            series_data = media_object._data
            tmdb_id = str(series_data.get("tmdbId", 0))
            dict_with_seasons["tmdb_id"] = tmdb_id
            if series_data:
                alternate_titles = self.extract_alternate_titles(
                    series_data.get("alternateTitles", [])
                )
                dict_with_seasons["alternate_titles"] = alternate_titles
            dict_with_seasons["title"] = (
                f"{dict_with_seasons['arr_title']} ({dict_with_seasons['media_year']})"
            )
            if tmdb_id != "0":
                dict_with_seasons["title"] = (
                    f"{dict_with_seasons['title']} {{tmdb-{tmdb_id}}}"
                )
            if tvdb_id != "0":
                dict_with_seasons["title"] = (
                    f"{dict_with_seasons['title']} {{tvdb-{tvdb_id}}}"
                )
            if imdb_id != "0":
                dict_with_seasons["title"] = (
                    f"{dict_with_seasons['title']} {{imdb-{imdb_id}}}"
                )

            for season in season_object:  # type: ignore
                season_dict = {
                    "season": "",
                    "has_episodes": True,
                }
                season_number = season.seasonNumber
                episode_count = getattr(season, "episodeFileCount", 0)
                has_episodes = episode_count > 0
                formatted_season = f"season{season_number:02}"

                season_dict["season"] = formatted_season
                season_dict["has_episodes"] = has_episodes
                dict_with_seasons["seasons"].append(season_dict)

            if any(
                season.get("has_episodes", False)
                for season in dict_with_seasons["seasons"]
            ):
                dict_with_seasons["has_episodes"] = True

            titles_with_seasons.append(dict_with_seasons)
        return titles_with_seasons

    def get_movies_with_years(
        self, all_movie_objects: list[Movie], instance_name: str, logger
    ) -> list[dict[str, str | list[str]]]:
        titles_with_years = []
        for media_object in all_movie_objects:
            dict_with_years = {
                "title": "",
                "id": None,
                "media_year": "",
                "years": [],
                "status": "",
                "has_file": False,
                "alternate_titles": [],
                "instance": instance_name,
            }
            path = Path(media_object.path)  # type: ignore
            movie_id = media_object.id
            title = media_object.title
            title_year = str(media_object.year)
            status = media_object.status
            has_file = media_object.hasFile
            imdb_id = str(media_object.imdbId)
            tmdb_id = str(media_object.tmdbId)
            # ugly to access the protected member, but needed for full data to avoid extra API calls
            movie_data = media_object._data
            alternate_titles = self.extract_movie_alternate_titles(
                movie_data.get("alternateTitles", [])
            )
            dict_with_years["alternate_titles"] = alternate_titles
            secondary_year = movie_data.get("secondaryYear", None)
            if secondary_year:
                dict_with_years["years"].append(str(secondary_year))
            dict_with_years["arr_title"] = title
            dict_with_years["status"] = status
            dict_with_years["has_file"] = has_file
            dict_with_years["id"] = movie_id
            dict_with_years["media_year"] = title_year
            dict_with_years["imdb_id"] = imdb_id
            dict_with_years["tmdb_id"] = tmdb_id
            dict_with_years["path"] = media_object.path
            dict_with_years["folder"] = path.name
            dict_with_years["title"] = (
                f"{dict_with_years['arr_title']} ({dict_with_years['media_year']})"
            )
            if tmdb_id != "0":
                dict_with_years["title"] = (
                    f"{dict_with_years['title']} {{tmdb-{tmdb_id}}}"
                )
            if imdb_id != "0":
                dict_with_years["title"] = (
                    f"{dict_with_years['title']} {{imdb-{imdb_id}}}"
                )

            titles_with_years.append(dict_with_years)
        return titles_with_years

    def extract_alternate_titles(self, alternate_titles_list):
        return [
            title_entry["title"].strip()
            for title_entry in alternate_titles_list
            if title_entry.get("title", "").strip()
        ]

    def extract_movie_alternate_titles(self, alternate_titles_list):
        return [
            title_entry["title"].strip()
            for title_entry in alternate_titles_list
            if title_entry.get("title", "").strip()
        ]


class Radarr(Media):
    def __init__(self, base_url: str, api: str, instance_name: str, logger: Logger):
        super().__init__()
        self.logger = logger
        try:
            self.radarr = RadarrAPI(base_url, api)
            self.instance_name = instance_name
            self.all_movie_objects = self.get_all_movies()
            self.movies = None
        except ArrApiUnauthorized as e:
            self.logger.error(
                "Error: Unauthorized access to Radarr. Please check your API key."
            )
            raise e
        except ConnectionFailure as e:
            self.logger.error(
                "Error: Connection to Radarr failed. Please check your base URL or network connection."
            )
            raise e

    # memoize this
    def get_movies_info(self):
        if not self.movies:
            self.movies = self.get_movies_with_years(
                self.all_movie_objects, self.instance_name, self.logger
            )
        return self.movies

    def get_all_movies(self) -> list[Movie]:
        return self.radarr.all_movies()

    def get_movie(self, id: int):
        movie_list = []
        movie = self.radarr.get_movie(id)
        movie_list.append(movie)
        return self.get_movies_with_years(movie_list, self.instance_name, self.logger)


class Sonarr(Media):
    def __init__(self, base_url: str, api: str, instance_name: str, logger: Logger):
        super().__init__()
        self.logger = logger
        try:
            self.sonarr = SonarrAPI(base_url, api)
            self.instance_name = instance_name
            self.all_series_objects = self.get_all_series()
            self.series = None
        except ArrApiUnauthorized as e:
            self.logger.error(
                "Error: Unauthorized access to Sonarr. Please check your API key."
            )
            raise e
        except ConnectionFailure as e:
            self.logger.error(
                "Error: Connection to Sonarr failed. Please check your base URL or network connection."
            )
            raise e

    # memoize this
    def get_series_info(self):
        if not self.series:
            self.series = self.get_series_with_seasons(
                self.logger, self.all_series_objects, self.instance_name
            )
        return self.series

    def get_all_series(self) -> list[Series]:
        return self.sonarr.all_series()

    def get_show(self, id: int):
        show_list = []
        show = self.sonarr.get_series(id)
        show_list.append(show)
        return self.get_series_with_seasons(self.logger, show_list, self.instance_name)


class Server:
    def __init__(
        self, plex_url: str, plex_token: str, library_names: list[str], logger: Logger
    ):
        self.logger = logger
        try:
            self.plex = PlexServer(plex_url, plex_token)
            self.library_names = library_names
            self.movie_collections, self.series_collections = self.get_collections()
        except PlexApiUnauthorized as e:
            self.logger.error(
                "Error: Unauthorized access to Plex. Please check your API key."
            )
            raise e
        except BadRequest as e:
            self.logger.error("Error: Bad request from Plex. Please check your config.")
            raise e

    def get_collections(self) -> tuple[list[str], list[str]]:
        movie_collections_list = []
        show_collections_list = []
        unique_collections = set()

        for library_name in self.library_names:
            try:
                library = self.plex.library.section(library_name)
            except UnknownType as e:
                self.logger.error(f"Library '{library_name}' is invalid: {e}")
                continue

            if library.type == "movie":
                self._movie_collection(
                    library, unique_collections, movie_collections_list
                )
            if library.type == "show":
                self._show_collection(
                    library, unique_collections, show_collections_list
                )
        return movie_collections_list, show_collections_list

    def _movie_collection(
        self,
        library: LibrarySection,
        unique_collections: set,
        movie_collections_list: list[str],
    ) -> None:
        collections = library.collections()
        for collection in collections:
            if collection.title not in unique_collections:
                unique_collections.add(collection.title)
                movie_collections_list.append(collection.title)

    def _show_collection(
        self,
        library: LibrarySection,
        unique_collections: set,
        show_collections_list: list[str],
    ) -> None:
        collections = library.collections()
        for collection in collections:
            if collection.title not in unique_collections:
                unique_collections.add(collection.title)
                show_collections_list.append(collection.title)

    def get_media(
        self, single_movie: bool = False, single_series: bool = False
    ) -> tuple[dict[str, dict], dict[str, dict]] | dict[str, dict]:
        movie_dict = {"movie": {}, "collections": {}}
        show_dict = {"show": {}, "collections": {}}
        fetch_collections = not (single_movie or single_series)

        for library_name in self.library_names:
            self.logger.debug(f"fetching library '{library_name}'")
            try:
                library = self.plex.library.section(library_name)
            except UnknownType as e:
                self.logger.error(f"Library '{library_name}' is invalid: {e}")
                continue
            self.logger.debug(f"finished fetching library '{library_name}'")
            if library.type == "movie" and not single_series:
                self._process_library(library, movie_dict, fetch_collections)
            if library.type == "show" and not single_movie:
                self._process_library(library, show_dict, fetch_collections)

        if single_movie:
            return movie_dict
        elif single_series:
            return show_dict
        else:
            return movie_dict, show_dict

    # largely taken from what Kometa does
    def get_all_with_paging(self, library):
        self.logger.info(
            f"Loading All {library.type.capitalize()}s from Library: {library.title}"
        )
        key = f"/library/sections/{library.key}/all?includeGuids=1&type={plexutils.searchType(library.type)}"
        container_start = 0
        container_size = plexapi.X_PLEX_CONTAINER_SIZE
        results = []
        total_size = 1
        while total_size > len(results) and container_start <= total_size:
            self.logger.debug(
                f"doing an iteration: total={total_size}, start={container_start}, size={container_size}"
            )
            data = library._server.query(
                key,
                headers={
                    "X-Plex-Container-Start": str(container_start),
                    "X-Plex-Container-Size": str(container_size),
                },
            )
            subresults = library.findItems(data, initpath=key)
            total_size = plexutils.cast(
                int, data.attrib.get("totalSize") or data.attrib.get("size")
            ) or len(subresults)

            librarySectionID = plexutils.cast(int, data.attrib.get("librarySectionID"))
            if librarySectionID:
                for item in subresults:
                    item.librarySectionID = librarySectionID

            results.extend(subresults)
            container_start += container_size
            self.logger.debug(
                f"Loaded: {total_size if container_start > total_size else container_start}/{total_size}"
            )

        self.logger.info(f"Loaded {total_size} {library.type.capitalize()}s")

        return results

    def _process_library(
        self,
        library: LibrarySection,
        item_dict: dict[str, dict],
        fetch_collections: bool = True,
    ) -> None:
        library_title = library.title
        if library_title not in item_dict[library.type]:
            item_dict[library.type][library_title] = {}
        if fetch_collections and library_title not in item_dict["collections"]:
            item_dict["collections"][library_title] = {}
        self.logger.debug(
            f"Getting all media items from library {library_title}, type={library.type}"
        )

        self.logger.debug("doing paging...")
        all_items = self.get_all_with_paging(library)
        self.logger.debug("done doing paging...")

        # all_items = library.all()
        self.logger.debug(
            f"finished getting all media items from library {library_title}, type={library.type}"
        )
        for item in all_items:
            title_key = item.title
            year = item.year or ""
            edition = getattr(item, "editionTitle", None)
            if edition:
                title_name = f"{title_key} ({year}) [{edition}]".strip()
            else:
                title_name = f"{title_key} ({year})".strip()

            item_dict[library.type][library_title][title_name] = item

        if fetch_collections:
            self.logger.debug(
                f"Getting all collections from library {library_title}, type={library.type}"
            )
            # hopefully this doesn't need to be paged as well?
            all_collections = library.collections()
            self.logger.debug(
                f"Finished getting all collections from library {library_title}, type={library.type}"
            )
            for collection in all_collections:
                collection_key = collection.title
                item_dict["collections"][library_title][collection_key] = collection

    def fetch_recently_added(self, media_type: str):
        recently_added_dict = {media_type: {}}
        for library_name in self.library_names:
            try:
                library = self.plex.library.section(library_name)
                if library.type == media_type:
                    self.logger.debug(
                        f"Fetching recently added items from library: '{library.title}', Type: '{library.type}'"
                    )
                    recently_added = library.recentlyAdded(maxresults=5)
                    if recently_added:
                        if library_name not in recently_added_dict[media_type]:
                            recently_added_dict[media_type][library_name] = {}

                        for item in recently_added:
                            title_key = item.title
                            year = item.year or ""
                            title_name = f"{title_key} ({year})".strip()
                            recently_added_dict[media_type][library_name][
                                title_name
                            ] = item
                        self.logger.info(
                            f"Fetched {len(recently_added)} recently added items from '{library_name}'"
                        )
                    else:
                        self.logger.info(
                            f"No recently added items found in library '{library_name}'"
                        )
            except UnknownType as e:
                self.logger.error(f"Library '{library_name}' is invalid: {e}")
                continue
            except Exception as e:
                self.logger.error(
                    f"An error occurred while fetching recently added items from '{library_name}': {e}"
                )
        return recently_added_dict if recently_added_dict[media_type] else None
