from dataclasses import dataclass
from enum import Enum
from multiprocessing import Manager

from modules.settings import Settings


class ProgressState(Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


@dataclass
class JobProgress:
    state: str
    value: int


class Progress:
    def __init__(self, manager) -> None:
        self._lock = manager.Lock()
        self.progress_map = manager.dict()
        self.progress_value = 0
        self.counters = manager.dict(
            {
                Settings.POSTER_RENAMERR.value: 0,
                Settings.PLEX_UPLOADERR.value: 0,
                Settings.DRIVE_SYNC.value: 0,
                Settings.BORDER_REPLACERR.value: 0,
                Settings.UNMATCHED_ASSETS.value: 0,
            }
        )

    def add_job(self, job_name) -> str:
        """
        Add a new job with a unique job id.

        Args: None

        Returns: str(job_id)
        """
        if not job_name or not isinstance(job_name, str):
            raise ValueError("job_name must be a non-empty string")

        job_name = job_name.lower().strip()
        with self._lock:
            if job_name not in self.counters:
                raise ValueError(f"Unknown job type: {job_name}")
            self.counters[job_name] += 1
            job_id = f"{job_name}_{self.counters[job_name]:04d}"

        self.progress_map[job_id] = {
            "state": ProgressState.PENDING.value,
            "value": 0,
        }
        return job_id

    def start_job(self, job_id: str) -> None:
        self.progress_map[job_id] = {
            "state": ProgressState.IN_PROGRESS.value,
            "value": 0,
        }

    def remove_job(self, job_id: str) -> None:
        if job_id in self.progress_map:
            del self.progress_map[job_id]

    def get_progress(self, job_id: str) -> dict | None:
        return self.progress_map.get(job_id)

    def __call__(self, job_id: str, value: int, state: ProgressState) -> None:
        if job_id in self.progress_map:
            self.progress_map[job_id] = {
                "state": state.value,
                "value": value,
            }


manager = Manager()
progress_instance = Progress(manager)
