from abc import ABC, abstractmethod
from enum import Enum
from logging import Logger


class NotificationEvent(str, Enum):
    RUN_START = "run_start"
    RUN_END = "run_end"
    RUN_ERROR = "run_error"
    RENAME_SUMMARY = "rename_summary"
    UPLOAD_SUMMARY = "upload_summary"
    WEBHOOK_ITEM_NOT_FOUND = "webhook_item_not_found"


class NotificationModule(str, Enum):
    POSTER_RENAMERR = "Poster Renamerr"
    UNMATCHED_ASSETS = "Unmatched Assets"
    PLEX_UPLOADERR = "Plex Uploaderr"
    DRIVE_SYNC = "Drive Sync"


class BaseNotifier(ABC):
    def __init__(self, url: str, logger: Logger) -> None:
        self.url = url
        self.logger = logger

    @abstractmethod
    def send(self, event: NotificationEvent, **kwargs) -> None: ...
