from dataclasses import dataclass


@dataclass(slots=True)
class Payload:
    log_level: int
    target_path: str
    asset_folders: bool
    border_setting: str | None
    custom_color: str | None
