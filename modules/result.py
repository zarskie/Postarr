from dataclasses import dataclass
from enum import Enum


class JobStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class TaskResult:
    success: bool
    data: dict | None = None
    message: str | None = None
