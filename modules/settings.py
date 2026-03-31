import os
from enum import Enum


class Settings(Enum):
    CONFIG_PATH = "/config/config.yaml"
    LOG_DIR = "/config/logs"
    ORIGINAL_POSTERS = "/config/original_posters"
    POSTER_RENAMERR = "poster_renamerr"
    UNMATCHED_ASSETS = "unmatched_assets"
    PLEX_UPLOADERR = "plex_uploaderr"
    BORDER_REPLACERR = "border_replacerr"
    DRIVE_SYNC = "drive_sync"
    MAIN = "main"
    DB_PATH = "/config/db/database.db"
    TIME_FORMAT = os.environ.get("TIME_FORMAT", "12")
