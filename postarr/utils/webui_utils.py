import logging
import os

from Payloads.border_replacerr_payload import Payload as BorderReplacerPayload
from Payloads.drive_sync_payload import Payload as DriveSyncPayload
from Payloads.plex_uploader_payload import Payload as PlexUploaderPayload
from Payloads.poster_renamerr_payload import Payload as PosterRenamerPayload
from Payloads.unmatched_assets_payload import Payload as UnmatchedAssetsPayload

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


def get_instances(model) -> dict[str, dict[str, str]]:
    instances = model.query.all()
    model_dict = {
        item.instance_name: {"url": item.url, "api": item.api_key} for item in instances
    }
    return model_dict


def create_poster_renamer_payload(radarr, sonarr, plex) -> PosterRenamerPayload:
    from postarr.models import PlexInstance, RadarrInstance, SonarrInstance
    from postarr.models.settings import Settings

    settings = Settings.query.first()
    log_level_str = getattr(settings, "log_level_poster_renamer", "").upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
    border_setting = settings.border_setting if settings else None
    custom_color = (
        "#000000"
        if border_setting == "black"
        else (settings.custom_color if settings else "")
    )
    poster_root = settings.poster_root if settings else ""
    raw_source_dirs = (
        settings.source_dirs.split(",") if settings and settings.source_dirs else []
    )
    source_dirs = [
        os.path.join(poster_root, d.strip()) for d in raw_source_dirs if d.strip()
    ]
    all_instances = (
        [i.instance_name for i in RadarrInstance.query.all()]
        + [i.instance_name for i in SonarrInstance.query.all()]
        + [i.instance_name for i in PlexInstance.query.all()]
    )

    return PosterRenamerPayload(
        log_level=log_level,
        source_dirs=source_dirs,
        target_path=settings.target_path if settings else "",
        asset_folders=bool(settings.asset_folders) if settings else False,
        clean_assets=bool(settings.clean_assets) if settings else False,
        unmatched_assets=bool(settings.unmatched_assets) if settings else False,
        replace_border=bool(settings.replace_border) if settings else False,
        border_setting=border_setting,
        custom_color=custom_color,
        upload_to_plex=bool(settings.upload_to_plex) if settings else False,
        match_alt=bool(settings.match_alt) if settings else False,
        only_unmatched=bool(settings.only_unmatched) if settings else False,
        drive_sync=bool(settings.drive_sync) if settings else False,
        reapply_posters=bool(settings.reapply_posters) if settings else False,
        library_names=settings.library_names.split(",")
        if settings and settings.library_names
        else [],
        instances=all_instances,
        radarr=radarr,
        sonarr=sonarr,
        plex=plex,
    )


def create_unmatched_assets_payload(radarr, sonarr, plex) -> UnmatchedAssetsPayload:
    from postarr.models import PlexInstance, RadarrInstance, SonarrInstance
    from postarr.models.settings import Settings

    settings = Settings.query.first()
    log_level_str = getattr(settings, "log_level_unmatched_assets", "").upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

    all_instances = (
        [i.instance_name for i in RadarrInstance.query.all()]
        + [i.instance_name for i in SonarrInstance.query.all()]
        + [i.instance_name for i in PlexInstance.query.all()]
    )

    return UnmatchedAssetsPayload(
        log_level=log_level,
        target_path=settings.target_path if settings else "",
        asset_folders=bool(settings.asset_folders) if settings else False,
        show_all_unmatched=settings.show_all_unmatched if settings else False,
        library_names=settings.library_names.split(",")
        if settings and settings.library_names
        else [],
        instances=all_instances,
        radarr=radarr,
        sonarr=sonarr,
        plex=plex,
    )


def create_plex_uploader_payload(radarr, sonarr, plex) -> PlexUploaderPayload:
    from postarr.models import PlexInstance, RadarrInstance, SonarrInstance
    from postarr.models.settings import Settings

    settings = Settings.query.first()
    log_level_str = getattr(settings, "log_level_plex_uploaderr", "").upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

    all_instances = (
        [i.instance_name for i in RadarrInstance.query.all()]
        + [i.instance_name for i in SonarrInstance.query.all()]
        + [i.instance_name for i in PlexInstance.query.all()]
    )

    return PlexUploaderPayload(
        log_level=log_level,
        asset_folders=bool(settings.asset_folders) if settings else False,
        reapply_posters=bool(settings.reapply_posters) if settings else False,
        library_names=settings.library_names.split(",")
        if settings and settings.library_names
        else [],
        instances=all_instances,
        plex=plex,
        radarr=radarr,
        sonarr=sonarr,
    )


def create_border_replacer_payload() -> BorderReplacerPayload:
    from postarr.models.settings import Settings

    settings = Settings.query.first()
    log_level_str = getattr(settings, "log_level_border_replacerr", "").upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

    border_setting = settings.border_setting if settings else None
    if border_setting == "black":
        custom_color = "#000000"
    elif border_setting == "remove":
        custom_color = ""
    else:
        custom_color = settings.custom_color if settings else ""

    return BorderReplacerPayload(
        log_level=log_level,
        asset_folders=bool(settings.asset_folders) if settings else False,
        target_path=settings.target_path if settings else "",
        border_setting=border_setting,
        custom_color=custom_color,
    )


def create_drive_sync_payload() -> DriveSyncPayload:
    from postarr.models.gdrives import GDrives
    from postarr.models.rclone import RCloneConf
    from postarr.models.settings import Settings

    settings = Settings.query.first()
    rclone_conf = RCloneConf.query.first()
    gdrives = GDrives.query.all()
    log_level_str = getattr(settings, "log_level_drive_sync", "").upper()
    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
    gdrives_list = [
        {
            "drive_name": g.drive_name,
            "drive_id": g.drive_id,
            "drive_location": g.drive_location,
        }
        for g in gdrives
    ]

    return DriveSyncPayload(
        log_level=log_level,
        client_id=getattr(rclone_conf, "client_id", ""),
        rclone_token=getattr(rclone_conf, "rclone_token", ""),
        rclone_secret=getattr(rclone_conf, "rclone_secret", ""),
        service_account=getattr(rclone_conf, "service_account", ""),
        gdrives=gdrives_list,
    )
