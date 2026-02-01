import hashlib
import re
import unicodedata
from logging import Logger
from pathlib import Path
from unidecode import unidecode

from DapsEX.media import Radarr, Server, Sonarr
from Payloads.poster_renamerr_payload import Payload as PosterRenamerPayload
from Payloads.unmatched_assets_payload import Payload as UnmatchedAssetsPayload


def get_combined_media_dict(
    radarr_instances: dict[str, Radarr], sonarr_instances: dict[str, Sonarr],
    logger: Logger
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
