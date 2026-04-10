import hashlib
import logging
import re
import unicodedata
from logging import Logger
from pathlib import Path

from tabulate import tabulate
from unidecode import unidecode

from modules.media import Radarr, Server, Sonarr
from Payloads.poster_renamerr_payload import Payload as PosterRenamerPayload
from Payloads.unmatched_assets_payload import Payload as UnmatchedAssetsPayload


def get_combined_media_dict(
    radarr_instances: dict[str, Radarr],
    sonarr_instances: dict[str, Sonarr],
) -> dict:
    combined_series_dict = {}
    combined_movies_dict = {}
    for radarr in radarr_instances.values():
        for movie in radarr.get_movies_info():
            movie_title = movie["title"]
            if movie_title not in combined_movies_dict:
                combined_movies_dict[movie_title] = movie
            else:
                existing_movie = combined_movies_dict[movie_title]
                if movie.get("has_file", False) and not existing_movie.get(
                    "has_file", False
                ):
                    existing_movie["has_file"] = True
    for sonarr in sonarr_instances.values():
        for series in sonarr.get_series_info():
            series_title = series["title"]
            if series_title not in combined_series_dict:
                combined_series_dict[series_title] = series
            else:
                existing_series = combined_series_dict[series_title]

                existing_seasons_lookup = {
                    season["season"]: season
                    for season in existing_series.get("seasons", [])
                }
                for season in series.get("seasons", []):
                    season_number = season["season"]
                    if season_number in existing_seasons_lookup:
                        if season.get("has_episodes", False):
                            existing_seasons_lookup[season_number]["has_episodes"] = (
                                True
                            )
                    else:
                        existing_seasons_lookup[season_number] = season
                combined_series_dict[series_title]["seasons"] = list(
                    existing_seasons_lookup.values()
                )

    final_dict = {
        "movies": list(combined_movies_dict.values()),
        "shows": list(combined_series_dict.values()),
    }
    return final_dict


def get_combined_collections_dict(
    plex_instances: dict[str, Server],
) -> dict:
    movie_collections = set()
    series_collections = set()
    for plex in plex_instances.values():
        movie_collections.update(plex.movie_collections)
        series_collections.update(plex.series_collections)

    return {"movies": list(movie_collections), "shows": list(series_collections)}


def hash_file(file_path: Path, logger: Logger) -> str:
    try:
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.exception(f"Error hashing file {file_path}: {e}")
        raise e


def is_valid_hex_color(color: str) -> bool:
    hex_color_pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
    return bool(re.match(hex_color_pattern, color))


def create_arr_instances(
    payload_class: PosterRenamerPayload | UnmatchedAssetsPayload,
    radarr_class: type[Radarr],
    sonarr_class: type[Sonarr],
    logger: Logger,
) -> tuple[dict[str, Radarr], dict[str, Sonarr]]:
    radarr_instances: dict[str, Radarr] = {}
    sonarr_instances: dict[str, Sonarr] = {}

    for key, value in payload_class.radarr.items():
        if key in payload_class.instances:
            radarr_name = f"{key}"
            radarr_instances[radarr_name] = radarr_class(
                base_url=value["url"],
                api=value["api"],
                instance_name=radarr_name,
                logger=logger,
            )
    for key, value in payload_class.sonarr.items():
        if key in payload_class.instances:
            sonarr_name = f"{key}"
            sonarr_instances[sonarr_name] = sonarr_class(
                base_url=value["url"],
                api=value["api"],
                instance_name=sonarr_name,
                logger=logger,
            )
    return radarr_instances, sonarr_instances


def create_plex_instances(
    payload: PosterRenamerPayload | UnmatchedAssetsPayload,
    plex_class: type[Server],
    logger: Logger,
) -> dict[str, Server]:
    plex_instances = {}
    for key, value in payload.plex.items():
        if key in payload.instances:
            plex_name = f"{key}"
            plex_instances[plex_name] = plex_class(
                plex_url=value["url"],
                plex_token=value["api"],
                library_names=payload.library_names,
                logger=logger,
            )
    return plex_instances


def remove_chars(file_name: str) -> str:
    # adding this prob removes the need for some of the lower items, but leave in for now
    file_name = unidecode(file_name)
    file_name = unicodedata.normalize("NFKC", file_name)
    file_name = unicodedata.normalize("NFD", file_name)
    file_name = file_name.replace("⁄", "/")
    file_name = re.sub(r"(\d+)/(\d+)", r"\1-\2", file_name)
    file_name = re.sub(r"[\u0300-\u036f]", "", file_name)
    file_name = re.sub(r"[\u00A0\u200B\u200C\u200D\u200E\u200F\uFEFF]", "", file_name)
    file_name = re.sub(r"[\u2013\u2014]", "-", file_name)
    file_name = re.sub(
        r"[\(\)\*\^;~\\`\[\]'\",.!?:_\u2018\u2019\u201B\u02BB]", "", file_name
    )
    file_name = remove_emojis(file_name)
    file_name = file_name.replace("&", "and")
    file_name = re.sub(r"/", "", file_name)
    file_name = re.sub(r"\++", "", file_name)
    file_name = re.sub(r"\-+", "", file_name)
    file_name = re.sub(r"\s+", " ", file_name).strip()
    file_name = file_name.lower()
    return file_name


def strip_id(name: str) -> str:
    """
    Strip tvdb/imdb/tmdb ID from movie title.
    """
    return re.sub(r"\s*[\{\[](?:tvdb|imdb|tmdb).*?[\}\]]", "", name).strip()


def remove_emojis(name: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols, etc.
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002700-\U000027bf"  # Dingbats
        "\U0001f1e0-\U0001f1ff"  # Flags
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", name)


def strip_year(name: str) -> str:
    return re.sub(r"\(\d{4}\)", "", name).strip()


def convert_day_of_week(day: str) -> str:
    day_map = {
        "0": "monday",
        "1": "tuesday",
        "2": "wednesday",
        "3": "thursday",
        "4": "friday",
        "5": "saturday",
        "6": "sunday",
    }
    reverse_map = {v: k for k, v in day_map.items()}

    return day_map.get(day, reverse_map.get(day.lower(), day))


def log_media_summary(logger, media_dict, media_type, title="Media Summary"):
    if not media_dict:
        return
    has_media = "has_file" if media_type == "movies" else "has_episodes"
    headers = [
        "Arr Title",
        "Folder Name",
        "Parent Folder",
        "ID",
        "Year",
        "Instance",
        "Has File" if media_type == "movies" else "Has Episodes",
        "TMDB",
    ]
    if media_type == "shows":
        headers.append("TVDB")
    rows = []
    for value in media_dict:
        entries = value if isinstance(value, list) else [value]
        for media in entries:
            path = Path(media.get("path", ""))
            row = [
                media.get("arr_title", ""),
                path.name,
                path.parent.name,
                media.get("id", ""),
                media.get("media_year", ""),
                media.get("instance", ""),
                "yes" if media.get(has_media, False) else "no",
                media.get("tmdb_id", ""),
            ]
            if media_type == "shows":
                row.append(media.get("tvdb_id", ""))
            rows.append(row)

    logger.debug(
        "\n### %s ###\n%s\n", title, tabulate(rows, headers=headers, tablefmt="simple")
    )


def log_collections_summary(logger, collections_dict, title="Collections Summary"):
    for collection_type, titles in collections_dict.items():
        if not titles:
            continue
        rows = [[t] for t in titles]
        table_str = tabulate(rows, headers=["Title"], tablefmt="simple")
        logger.debug(
            "\n### %s - %s ###\n%s\n", title, collection_type.capitalize(), table_str
        )


def _compress_seasons(seasons):
    if not seasons:
        return ""

    sorted_seasons = sorted(seasons, key=lambda s: s.get("season", ""))
    groups = []
    group_start = sorted_seasons[0]
    group_end = sorted_seasons[0]

    for season in sorted_seasons[1:]:
        if season.get("has_episodes") == group_end.get("has_episodes"):
            group_end = season
        else:
            groups.append((group_start, group_end, group_end.get("has_episodes")))
            group_start = season
            group_end = season
    groups.append((group_start, group_end, group_end.get("has_episodes")))

    parts = []
    for start, end, has_ep in groups:
        label = "yes" if has_ep else "no"
        if start["season"] == end["season"]:
            parts.append(f"S{start['season'][-2:]}({label})")
        else:
            parts.append(f"S{start['season'][-2:]}-S{end['season'][-2:]}({label})")

    return " ".join(parts)


def _season_sort_key(item):
    file_name = item[0]
    match = re.search(r"- Season (\d+)", file_name)
    if match:
        return int(match.group(1))
    return 999


def log_matched_files_summary(
    logger, matched_files, media_type, title="Matched Files Summary"
):
    if not matched_files:
        return

    if media_type == "movies":
        headers = [
            "Matched File",
            "Source",
            "Arr Title",
            "Year",
            "Instance",
            "Has File",
            "TMDB",
        ]
        rows = []
        for file_path, info in matched_files.items():
            match = info.get("match", {})
            rows.append(
                [
                    file_path.name,
                    file_path.parent.name,
                    match.get("arr_title") or match.get("title", ""),
                    match.get("media_year", ""),
                    match.get("instance", ""),
                    "yes" if match.get("has_file") else "no",
                    match.get("tmdb_id", ""),
                ]
            )
    else:
        headers = [
            "Matched File",
            "Source",
            "Arr Title",
            "Year",
            "Instance",
            "Series Has Episodes",
            "TMDB",
            "TVDB",
            "Seasons Have Episodes",
        ]
        shows = {}
        for file_path, info in matched_files.items():
            match = info.get("match", {})
            title_key = match.get("arr_title") or match.get("title", "")
            if title_key not in shows:
                shows[title_key] = {
                    "match": match,
                    "main_file": None,
                    "main_source": None,
                    "season_files": [],
                    "seasons": [],
                }
            is_season_file = (
                "- Season" in Path(file_path).name
                or "- Specials" in Path(file_path).name
            )
            if is_season_file:
                source = Path(file_path).parent.name
                shows[title_key]["season_files"].append((Path(file_path).name, source))
            else:
                shows[title_key]["main_file"] = Path(file_path).name
                shows[title_key]["main_source"] = Path(file_path).parent.name
                shows[title_key]["seasons"] = match.get("matched_season_info", [])
        rows = []
        for show_title, data in shows.items():
            match = data["match"]
            rows.append(
                [
                    data["main_file"] or "",
                    data["main_source"] or "",
                    show_title,
                    match.get("media_year", ""),
                    match.get("instance", ""),
                    "yes" if match.get("has_episodes") else "no",
                    match.get("tmdb_id", ""),
                    match.get("tvdb_id", ""),
                    _compress_seasons(data["seasons"]),
                ]
            )
            for file_name, source in sorted(data["season_files"], key=_season_sort_key):
                season_part = file_name.split("- ")[-1]
                rows.append([f"↳ {season_part}", source, "", "", "", "", "", "", ""])

    logger.debug(
        "\n### %s ###\n%s\n",
        title,
        tabulate(rows, headers=headers, tablefmt="simple"),
    )


def log_matched_collections_summary(
    logger, matched_collections, title="Matched Collections Summary"
):
    if not matched_collections:
        return

    rows = []
    for item in matched_collections:
        path = Path(item.get("file", ""))
        rows.append([path.name, path.parent.name, item.get("match", "")])

    logger.debug(
        "\n### %s ###\n%s\n",
        title,
        tabulate(rows, headers=["File", "Source", "Match"], tablefmt="simple"),
    )


def log_plex_media_summary(logger, plex_media_dict, title="Plex Media Summary"):
    if not plex_media_dict:
        return
    summary_rows = []
    for instance, sections in plex_media_dict.items():
        for section_type, libraries in sections.items():
            for _, items in libraries.items():
                summary_rows.append([instance, section_type, len(items)])
    logger.debug(
        "\n### %s ###\n%s\n",
        title,
        tabulate(
            summary_rows,
            headers=["Instance", "Type", "Count"],
            tablefmt="simple",
        ),
    )
    if not logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
        return
    for instance, sections in plex_media_dict.items():
        for section_type, libraries in sections.items():
            for _, items in libraries.items():
                rows = [[t, repr(item)] for t, item in items.items()]
                logger.trace(  # type: ignore[attr-defined]
                    "\n### %s | %s | %s ###\n%s\n",
                    title,
                    instance,
                    section_type,
                    tabulate(rows, headers=["Title", "Item"], tablefmt="simple"),
                )


def log_plex_media_summary_webhook(logger, media_dict, title="Plex Media Summary"):
    if not media_dict:
        return
    for library_title, items in media_dict.items():
        rows = [[t, repr(item)] for t, item in items.items()]
        logger.trace(  # type: ignore[attr-defined]
            "\n### %s | %s ###\n%s\n",
            title,
            library_title,
            tabulate(rows, headers=["Title", "Item"], tablefmt="simple"),
        )


def log_banner(logger, job_name, job_id):
    logger.info(f"### New {job_name} run | Job ID: {job_id} ###")


def normalize(obj):
    if isinstance(obj, dict):
        return {str(k): normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def parse_schedule_string(schedule_str: str, logger: Logger) -> list[dict[str, str]]:
    hourly_pattern = re.match(r"hourly\((\d{1,2})\)$", schedule_str)
    daily_pattern = re.match(
        r"daily\((\d{1,2}:\d{2}(?:\|\d{1,2}:\d{2})*)\)$", schedule_str
    )
    weekly_pattern = re.match(r"weekly\((\w+)@(\d{1,2}:\d{2})\)$", schedule_str)
    monthly_pattern = re.match(r"monthly\((\d{1,2})@(\d{1,2}:\d{2})\)$", schedule_str)
    cron_pattern = re.match(r"cron\((.+)\)$", schedule_str)

    try:
        if hourly_pattern:
            minute = hourly_pattern.group(1)
            minute = int(minute)
            if 1 <= minute <= 59:
                logger.debug(f"Parsing hourly schedule: every {minute} minutes")
                return [{"minute": f"*/{minute}"}]
            else:
                raise ValueError(
                    "Hourly schedule must have a minute value between 1 and 59."
                )

        if daily_pattern:
            times = daily_pattern.group(1).split("|")
            parsed_schedules = []
            for time in times:
                hour, minute = map(int, time.split(":"))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    parsed_schedules.append({"hour": str(hour), "minute": str(minute)})
                else:
                    raise ValueError(f"Invalid time format: {time}")
            logger.debug(f"Parsing daily schedules with times: {times}")
            return parsed_schedules

        if weekly_pattern:
            day, time = weekly_pattern.groups()
            hour, minute = map(int, time.split(":"))

            day_of_week = convert_day_of_week(day)

            if not day_of_week.isdigit():
                raise ValueError(
                    f"Weekly schedule must specify a valid day (e.g. Monday). Invalid value: {day_of_week}"
                )
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                logger.debug(f"Parsing weekly schedule: {day} at {hour}:{minute}")
                return [
                    {
                        "day_of_week": day_of_week,
                        "hour": str(hour),
                        "minute": str(minute),
                    }
                ]
            else:
                raise ValueError(
                    "Weekly schedule must have a valid hour (0-23) and minute (0-59)."
                )

        if monthly_pattern:
            day, time = monthly_pattern.groups()
            day, hour, minute = int(day), *map(int, time.split(":"))
            if 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59:
                logger.debug(f"Parsing monthly schedule: day {day} at {hour}:{minute}")
                return [{"day": str(day), "hour": str(hour), "minute": str(minute)}]
            else:
                raise ValueError(
                    "Monthly schedule must have day (1-31), hour (0-23), and minute (0-59)."
                )

        if cron_pattern:
            cron_expression = cron_pattern.group(1)
            minute, hour, day, month, day_of_week = cron_expression.split()
            logger.debug(f"Parsing cron schedule: {cron_expression}")
            return [
                {
                    "minute": str(minute),
                    "hour": str(hour),
                    "day": str(day),
                    "month": str(month),
                    "day_of_week": str(day_of_week),
                }
            ]

        raise ValueError(f"Invalid schedule format: {schedule_str}")

    except ValueError as e:
        logger.error(f"Invalid schedule format: {schedule_str}. Error: {e}")
        raise


def construct_schedule_time(parsed_schedule: dict) -> str:
    hour = parsed_schedule.get("hour", "*")
    minute = parsed_schedule.get("minute", "*")
    day_of_week = parsed_schedule.get("day_of_week", "")
    month = parsed_schedule.get("month", "*")
    day_of_month = parsed_schedule.get("day", "*")
    schedule_time_parts = []

    if minute.startswith("*/"):
        schedule_time_parts.append(f"every {minute[2:]} minutes")
    elif minute == "*":
        schedule_time_parts.append("every minute")
    else:
        schedule_time_parts.append(f"at {minute.zfill(2)} minutes past the hour")

    if hour.startswith("*/"):
        schedule_time_parts.append(f"every {hour[2:]} hours")
    elif hour == "*":
        if "every minute" not in schedule_time_parts[0]:
            schedule_time_parts.append("every hour")
    else:
        schedule_time_parts[-1] = f"at {str(hour).zfill(2)}:{str(minute).zfill(2)}"

    if day_of_week and day_of_week != "*":
        day_of_week = convert_day_of_week(day_of_week)
        schedule_time_parts.append(f"on {day_of_week}")

    if day_of_month != "*":
        schedule_time_parts.append(f"on day {day_of_month}")

    if month != "*":
        schedule_time_parts.append(f"in month {month}")

    return " ".join(schedule_time_parts)
