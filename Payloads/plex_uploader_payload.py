from dataclasses import dataclass


@dataclass(slots=True)
class Payload:
    log_level: int
    asset_folders: bool
    reapply_posters: bool
    library_names: list[str]
    instances: list[str]
    plex: dict[str, dict[str, str]]
    radarr: dict[str, dict[str, str]]
    sonarr: dict[str, dict[str, str]]
    webhook_initial_delay: int = 0
    webhook_retry_delay: int = 30
    webhook_max_retries: int = 10
