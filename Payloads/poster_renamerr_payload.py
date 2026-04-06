from dataclasses import dataclass


@dataclass(slots=True)
class Payload:
    log_level: int
    source_dirs: list[str]
    target_path: str
    asset_folders: bool
    clean_assets: bool
    unmatched_assets: bool
    replace_border: bool
    border_setting: str | None
    custom_color: str | None
    upload_to_plex: bool
    match_alt: bool
    drive_sync: bool
    only_unmatched: bool
    reapply_posters: bool
    library_names: list[str]
    instances: list[str]
    radarr: dict[str, dict[str, str]]
    sonarr: dict[str, dict[str, str]]
    plex: dict[str, dict[str, str]]
