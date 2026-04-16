import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from modules.border_replacerr import BorderReplacerr
from modules.drive_sync import DriveSync
from modules.logger import get_postarr_logger
from modules.plex_upload import PlexUploaderr
from modules.poster_renamerr import PosterRenamerr
from modules.progress import progress_instance
from modules.settings import Settings
from modules.unmatched_assets import UnmatchedAssets
from modules.utils import normalize
from postarr.config.config import Config
from postarr.utils import webui_utils
from postarr.utils.webui_utils import LOG_LEVELS, get_instances, sanitize_for_log

# all globals needs to be defined here
global_config = Config()
db = SQLAlchemy()
migrate = Migrate()
executor = ThreadPoolExecutor(max_workers=3)
scheduler = BackgroundScheduler()

# define all loggers
postarr_logger = get_postarr_logger()


def create_job_wrapper(func, sched_id, app_instance):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        update_single_schedule_next_run(app_instance, sched_id)
        return result

    return wrapper


def update_single_schedule_next_run(app, schedule_id):
    with app.app_context():
        try:
            from postarr import models

            schedule = models.Schedule.query.get(schedule_id)
            if schedule:
                job = scheduler.get_job(f"{schedule.module}-{schedule.id}")
                if job:
                    next_run = getattr(job, "next_run_time", None)
                    if next_run:
                        schedule.next_run = next_run.strftime("%b %d, %Y %I:%M %p")
                        db.session.commit()
                        postarr_logger.debug(
                            "Updated next run for %s: %s",
                            schedule.module,
                            schedule.next_run,
                        )
        except Exception as e:
            postarr_logger.error("Error updating single next run: %s", e)


def load_schedules_from_db(app):
    with app.app_context():
        try:
            from postarr import models

            scheduler.remove_all_jobs()
            postarr_logger.debug("Cleared existing scheduler jobs")

            MODULE_JOBS = {
                "poster-renamerr": lambda: run_renamer_task(app),
                "unmatched-assets": lambda: run_unmatched_assets_task(app),
                "plex-uploaderr": lambda: run_plex_uploaderr_task(app),
                "drive-sync": lambda: run_drive_sync_task(app),
            }
            schedules = models.Schedule.query.all()
            postarr_logger.debug("Found %s schedule(s) in database", len(schedules))

            for schedule in schedules:
                job_func = MODULE_JOBS.get(schedule.module)
                if not job_func:
                    postarr_logger.warning("Unknown module: %s", schedule.module)
                    continue
                if schedule.schedule_type == "cron":
                    trigger = CronTrigger.from_crontab(schedule.schedule_value)
                elif schedule.schedule_type == "interval":
                    minutes = int(schedule.schedule_value)
                    trigger = IntervalTrigger(minutes=minutes)
                else:
                    postarr_logger.warning(
                        "Unknown schedule type: %s for %s",
                        schedule.schedule_type,
                        schedule.module,
                    )
                    continue

                scheduler.add_job(
                    func=create_job_wrapper(job_func, schedule.id, app),
                    trigger=trigger,
                    id=f"{schedule.module}-{schedule.id}",
                    replace_existing=True,
                )
                postarr_logger.info("Scheduled job %s", schedule.module)
        except Exception as e:
            postarr_logger.error("Error loading schedules: %s", e)


def update_next_run_times(app):
    with app.app_context():
        try:
            from postarr import models

            schedules = models.Schedule.query.all()
            for schedule in schedules:
                job = scheduler.get_job(f"{schedule.module}-{schedule.id}")
                if job:
                    next_run = getattr(job, "next_run_time", None)
                    if next_run:
                        fmt = (
                            "%b %d, %Y %H:%M"
                            if Settings.TIME_FORMAT.value == "24"
                            else "%b %d, %Y %I:%M %p"
                        )
                        schedule.next_run = next_run.strftime(fmt)
                        postarr_logger.debug(
                            "[%s] next run scheduled for %s",
                            schedule.module,
                            schedule.next_run,
                        )
                    else:
                        schedule.next_run = "Pending"
                        postarr_logger.warning(
                            "[%s] has no next run time - marked Pending",
                            schedule.module,
                        )
                else:
                    schedule.next_run = "N/A"
                    postarr_logger.warning(
                        "[%s--%s] job not found in scheduler",
                        schedule.module,
                        schedule.id,
                    )
            db.session.commit()
        except Exception as e:
            postarr_logger.error("Error updating next run times: %s", e)


def create_app() -> Flask:
    # init flask app
    app = Flask(__name__, static_folder=None)
    app.config.from_object(global_config)
    Config.init_directories()
    react_folder = os.path.join(app.root_path, "..", "frontend", "dist")

    # initiate database
    db.init_app(app)
    migrate.init_app(app, db)

    if app.debug:
        with app.app_context():
            version = os.getenv("VERSION", "dev")
            postarr_logger.info("Starting Postarr v%s", version)
            with db.engine.connect() as conn:
                conn.execute(db.text("PRAGMA journal_mode=WAL;"))
            load_schedules_from_db(app)
            if not scheduler.running:
                scheduler.start()
                postarr_logger.info("Scheduler started")
            else:
                postarr_logger.warning("Scheduler already running - skipping start")
            update_next_run_times(app)

    # import needed blueprints
    from postarr.views.poster_renamer.poster_renamer import poster_renamer
    from postarr.views.poster_search.poster_search import poster_search
    from postarr.views.settings.settings import settings

    app.register_blueprint(settings, url_prefix="/api/settings")
    app.register_blueprint(poster_renamer, url_prefix="/api/poster-renamer")
    app.register_blueprint(poster_search, url_prefix="/api/poster-search")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_react(path):
        file_path = os.path.join(react_folder, path)
        if path != "" and os.path.exists(file_path):
            return send_from_directory(react_folder, path)
        return send_from_directory(react_folder, "index.html")

    return app


def run_renamer_task(
    app, webhook_item: dict | None = None, overrides: dict | None = None
):
    job_id: str | None = None

    def remove_job(failed: bool = False, e: Exception | None = None):
        if not job_id:
            return
        try:
            if failed and e:
                progress_instance.fail_job(postarr_logger, e, job_id)
            else:
                progress_instance.complete_job(postarr_logger, job_id)
        except Exception as e:
            postarr_logger.error("Error cleaning up job '%s': %s", job_id, e)

    with app.app_context():
        from postarr.models import PlexInstance, RadarrInstance, SonarrInstance

        try:
            radarr = get_instances(RadarrInstance)
            sonarr = get_instances(SonarrInstance)
            plex = get_instances(PlexInstance)
            poster_renamer_payload = webui_utils.create_poster_renamer_payload(
                radarr, sonarr, plex
            )
            if overrides:
                if "logLevel" in overrides:
                    log_level_str = overrides["logLevel"].upper()
                    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
                    poster_renamer_payload.log_level = log_level
                if "unmatchedAssets" in overrides:
                    poster_renamer_payload.unmatched_assets = overrides[
                        "unmatchedAssets"
                    ]
                if "unmatchedOnly" in overrides:
                    poster_renamer_payload.only_unmatched = overrides["unmatchedOnly"]
                if "plexUpload" in overrides:
                    poster_renamer_payload.upload_to_plex = overrides["plexUpload"]
                if "matchAltTitles" in overrides:
                    poster_renamer_payload.match_alt = overrides["matchAltTitles"]
                if "driveSync" in overrides:
                    poster_renamer_payload.drive_sync = overrides["driveSync"]

            job_id = progress_instance.add_job(
                postarr_logger, Settings.POSTER_RENAMERR.value
            )

            renamer = PosterRenamerr(poster_renamer_payload)

            def check_borders() -> bool:
                from postarr.utils.database import Database

                with app.app_context():
                    postarr_logger.debug("Checking borders on first file in file cache")
                    db_instance = Database(db, postarr_logger)
                    first_file_settings = db_instance.get_first_file_settings()
                    postarr_logger.trace(  # type: ignore[attr-defined]
                        "Found first file setting: %s", first_file_settings
                    )
                    if not first_file_settings:
                        return False
                    return (
                        first_file_settings.get("border_setting")
                        != poster_renamer_payload.border_setting
                        or first_file_settings.get("custom_color")
                        != poster_renamer_payload.custom_color
                    )

            def run_renamerr_callback(fut):
                try:
                    media_dict = fut.result()
                    if poster_renamer_payload.unmatched_assets:
                        postarr_logger.info(
                            "Poster renamerr completed, starting unmatched assets"
                        )
                        unmatched_future = executor.submit(
                            handle_unmatched_assets_task,
                            app,
                            radarr,
                            sonarr,
                            plex,
                            chained=True,
                        )
                        remove_job()
                        if poster_renamer_payload.upload_to_plex:
                            unmatched_future.add_done_callback(
                                lambda _: run_unmatched_after_renamerr_callback(
                                    media_dict
                                )
                            )

                    elif poster_renamer_payload.upload_to_plex:
                        if media_dict:
                            postarr_logger.trace(  # type: ignore[attr-defined]
                                "Media dict from renamer:\n%s",
                                json.dumps(
                                    normalize(media_dict), indent=2, ensure_ascii=False
                                ),
                            )
                        else:
                            postarr_logger.debug(  # type: ignore[attr-defined]
                                "No media dict from renamer. Proceeding with full upload."
                            )
                        remove_job()
                        executor.submit(
                            handle_plex_uploaderr_task,
                            app,
                            plex,
                            radarr,
                            sonarr,
                            webhook_item,
                            media_dict,
                            chained=True,
                        )
                    else:
                        remove_job()

                except Exception as e:
                    postarr_logger.error("Error in run_renamerr_callback: %s", e)
                    remove_job()

            def run_border_replacerr_callback(_):
                try:
                    postarr_logger.info(
                        "Border replacerr completed, starting poster renamerr (unmatched only)"
                    )
                    postarr_logger.trace(  # type: ignore[attr-defined]
                        "Poster Renamerr Payload:\n%s",
                        json.dumps(
                            sanitize_for_log(poster_renamer_payload),
                            indent=2,
                            default=str,
                        ),
                    )
                    renamer_future = executor.submit(
                        renamer.run, progress_instance, job_id
                    )
                    renamer_future.add_done_callback(run_renamerr_callback)
                except Exception as e:
                    postarr_logger.error(
                        "Error in run_border_replacerr_callback: %s", e
                    )
                    remove_job()

            def run_unmatched_after_renamerr_callback(media_dict):
                try:
                    postarr_logger.info(
                        "Unmatched assets completed, starting plex uploaderr"
                    )
                    if media_dict:
                        postarr_logger.trace(  # type: ignore[attr-defined]
                            "Media dict from renamerr:\n%s",
                            json.dumps(
                                normalize(media_dict),
                                indent=2,
                                ensure_ascii=False,
                            ),
                        )
                    else:
                        postarr_logger.debug(
                            "No media dict from renamer. Proceeding with full upload."
                        )
                    executor.submit(
                        handle_plex_uploaderr_task,
                        app,
                        plex,
                        radarr,
                        sonarr,
                        webhook_item,
                        media_dict,
                        chained=True,
                    )
                except Exception as e:
                    postarr_logger.error(
                        "Error in run_unmatched_after_renamerr_callback: %s", e
                    )

            def run_unmatched_assets_only_unmatched_callback(_):
                try:
                    if check_borders():
                        postarr_logger.info(
                            "Unmatched assets completed, border setting change detected — starting border replacerr"
                        )
                        border_replacerr_future = executor.submit(
                            run_border_replacer_task, app
                        )
                        border_replacerr_future.add_done_callback(
                            run_border_replacerr_callback
                        )
                    else:
                        postarr_logger.info(
                            "Unmatched assets completed, starting poster renamerr (unmatched only)"
                        )
                        postarr_logger.trace(  # type: ignore[attr-defined]
                            "Poster Renamerr Payload:\n%s",
                            json.dumps(
                                sanitize_for_log(poster_renamer_payload),
                                indent=2,
                                default=str,
                            ),
                        )
                        renamer_future = executor.submit(
                            renamer.run, progress_instance, job_id
                        )
                        renamer_future.add_done_callback(run_renamerr_callback)
                except Exception as e:
                    postarr_logger.error(
                        "Error in run_unmatched_assets_only_unmatched_callback: %s", e
                    )
                    remove_job()

            def run_drive_sync_callback(_):
                try:
                    if (
                        poster_renamer_payload.unmatched_assets
                        and poster_renamer_payload.only_unmatched
                    ):
                        postarr_logger.info(
                            "Drive sync task completed, starting unmatched assets"
                        )
                        unmatched_future = executor.submit(
                            handle_unmatched_assets_task,
                            app,
                            radarr,
                            sonarr,
                            plex,
                            chained=True,
                        )
                        unmatched_future.add_done_callback(
                            run_unmatched_assets_only_unmatched_callback
                        )
                    else:
                        postarr_logger.info(
                            "Drive sync completed, starting poster renamerr"
                        )
                        postarr_logger.trace(  # type: ignore[attr-defined]
                            "Poster Renamerr Payload:\n%s",
                            json.dumps(
                                sanitize_for_log(poster_renamer_payload),
                                indent=2,
                                default=str,
                            ),
                        )
                        renamer_future = executor.submit(
                            renamer.run, progress_instance, job_id
                        )
                        renamer_future.add_done_callback(run_renamerr_callback)
                except Exception as e:
                    postarr_logger.error("Error in run_drive_sync_callback: %s", e)
                    remove_job()

            if webhook_item:
                postarr_logger.debug("Starting poster renamerr (webhook)")
                future = executor.submit(
                    renamer.run,
                    progress_instance,
                    job_id,
                    webhook_item,
                )
                future.add_done_callback(run_renamerr_callback)
            else:
                if poster_renamer_payload.drive_sync:
                    postarr_logger.info("Starting drive sync")
                    drive_sync_future = executor.submit(
                        run_drive_sync_task, app, chained=True
                    )
                    drive_sync_future.add_done_callback(run_drive_sync_callback)
                elif (
                    poster_renamer_payload.unmatched_assets
                    and poster_renamer_payload.only_unmatched
                ):
                    postarr_logger.info("Starting unmatched assets")
                    unmatched_future = executor.submit(
                        handle_unmatched_assets_task,
                        app,
                        radarr,
                        sonarr,
                        plex,
                        chained=True,
                    )
                    unmatched_future.add_done_callback(
                        run_unmatched_assets_only_unmatched_callback
                    )
                else:
                    postarr_logger.info("Starting poster renamerr")
                    postarr_logger.trace(  # type: ignore[attr-defined]
                        "Poster Renamerr Payload:\n%s",
                        json.dumps(
                            sanitize_for_log(poster_renamer_payload),
                            indent=2,
                            default=str,
                        ),
                    )
                    renamer_future = executor.submit(
                        renamer.run, progress_instance, job_id
                    )
                    renamer_future.add_done_callback(run_renamerr_callback)

            return {
                "message": "Poster renamer task started",
                "job_id": job_id,
                "success": True,
            }
        except Exception as e:
            postarr_logger.error("Error in Poster Renamer Task: %s", e)
            remove_job(failed=True, e=e)
            return {"success": False, "message": str(e)}


def run_border_replacer_task(
    app, overrides: dict | None = None, chained: bool = False
) -> dict:
    job_id: str | None = None
    try:
        with app.app_context():
            from postarr.utils.database import Database

            db_instance = Database(db, postarr_logger)
            first_file_settings = db_instance.get_first_file_settings()

            border_replacerr_payload = webui_utils.create_border_replacer_payload()
            if overrides:
                if "logLevel" in overrides:
                    log_level_str = overrides["logLevel"].upper()
                    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
                    border_replacerr_payload.log_level = log_level
                if "borderSetting" in overrides:
                    border_replacerr_payload.border_setting = overrides.get(
                        "borderSetting", border_replacerr_payload.border_setting
                    )
                if "customColor" in overrides:
                    border_replacerr_payload.custom_color = overrides.get(
                        "customColor", border_replacerr_payload.custom_color
                    )

            if not border_replacerr_payload.custom_color:
                border_replacerr_payload.custom_color = None
            border_setting = border_replacerr_payload.border_setting
            custom_color = border_replacerr_payload.custom_color

            def remove_job_cb(fut):
                try:
                    fut.result()
                except Exception as e:
                    if job_id:
                        progress_instance.fail_job(postarr_logger, e, job_id)
                else:
                    if job_id:
                        progress_instance.complete_job(postarr_logger, job_id)

            if first_file_settings:
                current_border_setting = first_file_settings.get("border_setting")
                current_custom_color = first_file_settings.get("custom_color")

                if (
                    current_border_setting == border_setting
                    and current_custom_color == custom_color
                ):
                    postarr_logger.info(
                        "Skipping border replacerr: settings already applied (border=%s, color=%s)",
                        border_setting,
                        custom_color,
                    )
                    return {
                        "message": "Border and color settings already applied. Task skipped.",
                        "success": True,
                        "job_id": None,
                    }

            job_id = progress_instance.add_job(
                postarr_logger, Settings.BORDER_REPLACERR.value
            )
            postarr_logger.trace(  # type: ignore[attr-defined]
                "Border Replacerr Payload:\n%s",
                json.dumps(
                    sanitize_for_log(border_replacerr_payload), indent=2, default=str
                ),
            )
            border_replacerr = BorderReplacerr(payload=border_replacerr_payload)
            if chained:
                postarr_logger.debug("Starting border replacerr (chained)")
                try:
                    border_replacerr.replace_current_assets(progress_instance, job_id)
                    progress_instance.complete_job(postarr_logger, job_id)
                except Exception as e:
                    progress_instance.fail_job(postarr_logger, e, job_id)
            else:
                postarr_logger.info("Starting border replacerr")
                future = executor.submit(
                    border_replacerr.replace_current_assets, progress_instance, job_id
                )
                future.add_done_callback(remove_job_cb)

            return {
                "message": "Border replacer task started",
                "job_id": job_id,
                "success": True,
            }

    except Exception as e:
        if job_id:
            progress_instance.fail_job(postarr_logger, e, job_id)
        return {"success": False, "message": str(e)}


def handle_unmatched_assets_task(
    app, radarr, sonarr, plex, overrides: dict | None = None, chained: bool = False
) -> dict:
    job_id: str | None = None
    try:
        with app.app_context():
            unmatched_assets_payload = webui_utils.create_unmatched_assets_payload(
                radarr, sonarr, plex
            )
            if overrides:
                if "logLevel" in overrides:
                    log_level_str = overrides["logLevel"].upper()
                    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
                    unmatched_assets_payload.log_level = log_level

            job_id = progress_instance.add_job(
                postarr_logger, Settings.UNMATCHED_ASSETS.value
            )
            postarr_logger.trace(  # type: ignore[attr-defined]
                "Unmatched Assets Payload:\n%s",
                json.dumps(
                    sanitize_for_log(unmatched_assets_payload), indent=2, default=str
                ),
            )
            unmatched_assets = UnmatchedAssets(unmatched_assets_payload)

            def remove_job_cb(fut):
                try:
                    fut.result()
                except Exception as e:
                    progress_instance.fail_job(postarr_logger, e, job_id)
                else:
                    progress_instance.complete_job(postarr_logger, job_id)

            if chained:
                postarr_logger.debug("Starting unmatched assets (chained)")
                try:
                    unmatched_assets.run(progress_instance, job_id)
                    progress_instance.complete_job(postarr_logger, job_id)
                except Exception as e:
                    progress_instance.fail_job(postarr_logger, e, job_id)
            else:
                postarr_logger.info("Starting unmatched assets")
                future = executor.submit(
                    unmatched_assets.run,
                    progress_instance,
                    job_id,
                )
                future.add_done_callback(remove_job_cb)

            return {
                "message": "Unmatched assets task started",
                "job_id": job_id,
                "success": True,
            }

    except Exception as e:
        if job_id:
            progress_instance.fail_job(postarr_logger, e, job_id)
        return {"success": False, "message": str(e)}


def handle_plex_uploaderr_task(
    app,
    plex,
    radarr,
    sonarr,
    webhook_item: dict | None = None,
    media_dict: dict | None = None,
    overrides: dict | None = None,
    chained: bool = False,
) -> dict:
    job_id: str | None = None
    try:
        with app.app_context():
            plex_uploader_payload = webui_utils.create_plex_uploader_payload(
                radarr, sonarr, plex
            )
            if overrides:
                if "logLevel" in overrides:
                    log_level_str = overrides["logLevel"].upper()
                    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
                    plex_uploader_payload.log_level = log_level
                if "reapplyPosters" in overrides:
                    plex_uploader_payload.reapply_posters = overrides["reapplyPosters"]

            job_id = progress_instance.add_job(
                postarr_logger, Settings.PLEX_UPLOADERR.value
            )
            postarr_logger.trace(  # type: ignore[attr-defined]
                "Plex Uploaderr Payload:\n%s",
                json.dumps(
                    sanitize_for_log(plex_uploader_payload), indent=2, default=str
                ),
            )

            def remove_job_cb(fut):
                try:
                    fut.result()
                except Exception as e:
                    progress_instance.fail_job(postarr_logger, e, job_id)
                else:
                    progress_instance.complete_job(postarr_logger, job_id)

            if webhook_item and media_dict:
                postarr_logger.info("Starting plex uploaderr (webhook)")
                plex_uploaderr = PlexUploaderr(
                    plex_uploader_payload,
                    webhook_item=webhook_item,
                    media_dict=media_dict,
                )
                future = executor.submit(plex_uploaderr.upload_posters_webhook, job_id)
                future.add_done_callback(remove_job_cb)
            else:
                plex_uploaderr = PlexUploaderr(plex_uploader_payload)

                if chained:
                    postarr_logger.debug("Starting plex uploaderr (chained)")
                    try:
                        plex_uploaderr.upload_posters_full(progress_instance, job_id)
                        progress_instance.complete_job(postarr_logger, job_id)
                    except Exception as e:
                        progress_instance.fail_job(postarr_logger, e, job_id)
                else:
                    postarr_logger.info("Starting plex uploaderr")
                    future = executor.submit(
                        plex_uploaderr.upload_posters_full,
                        progress_instance,
                        job_id,
                    )
                    future.add_done_callback(remove_job_cb)

            return {
                "message": "Plex uploaderr task started",
                "job_id": job_id,
                "success": True,
            }
    except Exception as e:
        if job_id:
            progress_instance.fail_job(postarr_logger, e, job_id)
        return {"success": False, "message": str(e)}


def run_unmatched_assets_task(app, overrides: dict | None = None):
    from postarr.models import PlexInstance, RadarrInstance, SonarrInstance

    try:
        with app.app_context():
            radarr = get_instances(RadarrInstance)
            sonarr = get_instances(SonarrInstance)
            plex = get_instances(PlexInstance)

        return handle_unmatched_assets_task(
            app, radarr, sonarr, plex, overrides=overrides
        )
    except Exception as e:
        postarr_logger.error("Error in unmatched assets task: %s", e)
        return {"success": False, "message": str(e)}


def run_plex_uploaderr_task(app, overrides: dict | None = None):
    from postarr.models import PlexInstance, RadarrInstance, SonarrInstance

    try:
        with app.app_context():
            radarr = get_instances(RadarrInstance)
            sonarr = get_instances(SonarrInstance)
            plex = get_instances(PlexInstance)

        return handle_plex_uploaderr_task(
            app, plex, radarr, sonarr, overrides=overrides
        )
    except Exception as e:
        postarr_logger.error("Error in plex uploaderr task: %s", e)
        return {"success": False, "message": str(e)}


def run_drive_sync_task(
    app, overrides: dict | None = None, chained: bool = False
) -> dict:
    from postarr.views.poster_search.poster_search import reset_cache

    job_id: str | None = None
    try:
        with app.app_context():
            drive_sync_payload = webui_utils.create_drive_sync_payload()
            if overrides:
                if "logLevel" in overrides:
                    log_level_str = overrides["logLevel"].upper()
                    log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
                    drive_sync_payload.log_level = log_level
            has_oauth = all(
                [
                    drive_sync_payload.client_id,
                    drive_sync_payload.oauth_token,
                    drive_sync_payload.client_secret,
                ]
            )
            has_service_account = bool(drive_sync_payload.service_account)
            if not has_oauth and not has_service_account:
                postarr_logger.error(
                    "Drive sync requires either OAuth credentials (client_id, client_secret, oauth_token) "
                    "or a service account — neither is configured"
                )
                return {
                    "success": False,
                    "message": "Drive sync credentials not configured",
                }

            job_id = progress_instance.add_job(
                postarr_logger, Settings.DRIVE_SYNC.value
            )
            postarr_logger.trace(  # type: ignore[attr-defined]
                "Drive Sync Payload:\n%s",
                json.dumps(sanitize_for_log(drive_sync_payload), indent=2, default=str),
            )
            drive_sync = DriveSync(drive_sync_payload)

            def remove_job_cb(fut):
                try:
                    fut.result()
                except Exception as e:
                    if job_id:
                        progress_instance.fail_job(postarr_logger, e, job_id)
                else:
                    reset_cache()
                    progress_instance.complete_job(postarr_logger, job_id)

            if chained:
                postarr_logger.debug("Starting drive sync (chained)")
                try:
                    drive_sync.sync_all_drives(progress_instance, job_id)
                    reset_cache()
                    progress_instance.complete_job(postarr_logger, job_id)
                except Exception as e:
                    progress_instance.fail_job(postarr_logger, e, job_id)
            else:
                postarr_logger.info("Starting drive sync")
                future = executor.submit(
                    drive_sync.sync_all_drives, progress_instance, job_id
                )
                future.add_done_callback(remove_job_cb)

            return {
                "message": "Drive Sync task started",
                "job_id": job_id,
                "success": True,
            }
    except Exception as e:
        if job_id:
            progress_instance.fail_job(postarr_logger, e, job_id)
        return {"success": False, "message": str(e)}


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
