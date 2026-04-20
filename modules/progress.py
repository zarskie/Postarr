from enum import Enum
from logging import Logger
from threading import Lock
from time import sleep

from modules.settings import Settings


class ProgressState(Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class Progress:
    def __init__(self) -> None:
        self._lock = Lock()
        self._progress_map: dict[str, dict] = {}
        self._counters: dict[str, int] = {
            Settings.POSTER_RENAMERR.value: 0,
            Settings.PLEX_UPLOADERR.value: 0,
            Settings.DRIVE_SYNC.value: 0,
            Settings.BORDER_REPLACERR.value: 0,
            Settings.UNMATCHED_ASSETS.value: 0,
        }

    def add_job(self, logger: Logger, job_name: str) -> str:
        if not job_name or not isinstance(job_name, str):
            raise ValueError(f"job_name must be a non-empty string, got: {job_name!r}")

        job_name = job_name.lower().strip()
        with self._lock:
            if job_name not in self._counters:
                raise ValueError(f"Unknown job type: {job_name}")
            self._counters[job_name] += 1
            job_id = f"{job_name}_{self._counters[job_name]:04d}"
            self._progress_map[job_id] = {
                "state": ProgressState.PENDING.value,
                "value": 0,
            }
            logger.debug("'%s' job has been added", job_id)
        return job_id

    def start_job(self, job_id: str) -> None:
        with self._lock:
            self._update(job_id, ProgressState.IN_PROGRESS, 0)

    def fail_job(
        self, logger: Logger, job_id: str, e: Exception | str | None = None
    ) -> None:
        with self._lock:
            self._update(job_id, ProgressState.FAILED, 0)
            logger.error("'%s' job failed with error: %s", job_id, e)
        sleep(2)
        self.remove_job(job_id)

    def complete_job(self, logger: Logger, job_id: str) -> None:
        with self._lock:
            self._update(job_id, ProgressState.COMPLETED, 100)
            logger.debug("'%s' job has been removed", job_id)
        sleep(2)
        self.remove_job(job_id)

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._progress_map.pop(job_id, None)

    def get_progress(self, job_id: str) -> dict | None:
        with self._lock:
            return self._progress_map.get(job_id)

    def get_all_progress(self) -> dict:
        with self._lock:
            return dict(self._progress_map)

    def __call__(self, job_id: str, value: int, state: ProgressState) -> None:
        with self._lock:
            self._update(job_id, state, value)

    def _update(self, job_id: str, state: ProgressState, value: int) -> None:
        if job_id in self._progress_map:
            self._progress_map[job_id] = {
                "state": state.value,
                "value": value,
            }


progress_instance = Progress()
