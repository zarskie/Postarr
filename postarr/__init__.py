import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from pprint import pformat
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from modules.border_replacerr import BorderReplacerr
from modules.drive_sync import DriveSync
from modules.plex_upload import PlexUploaderr
from modules.poster_renamerr import PosterRenamerr
from modules.settings import Settings
from modules.unmatched_assets import UnmatchedAssets
from postarr.config.config import Config
from postarr.utils import webui_utils
from postarr.utils.logger_utils import get_postarr_logger
from postarr.utils.webui_utils import LOG_LEVELS, get_instances
from progress import ProgressState, progress_instance

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
                            f"Updated next run for {schedule.module}: {schedule.next_run}"
                        )
        except Exception as e:
            postarr_logger.error(f"Error updating single next run: {e}")


def load_schedules_from_db(app):
    with app.app_context():
        try:
            from postarr import models

            scheduler.remove_all_jobs()

            MODULE_JOBS = {
                "poster-renamerr": lambda: run_renamer_task(app),
                "unmatched-assets": lambda: run_unmatched_assets_task(app),
                "plex-uploaderr": lambda: run_plex_uploaderr_task(app),
                "drive-sync": lambda: run_drive_sync_task(app),
            }
            schedules = models.Schedule.query.all()
            for schedule in schedules:
                job_func = MODULE_JOBS.get(schedule.module)
                if not job_func:
                    postarr_logger.warning(f"Unknown module: {schedule.module}")
                    continue
                if schedule.schedule_type == "cron":
                    trigger = CronTrigger.from_crontab(schedule.schedule_value)
                elif schedule.schedule_type == "interval":
                    minutes = int(schedule.schedule_value)
                    trigger = IntervalTrigger(minutes=minutes)
                else:
                    postarr_logger.warning(
                        f"Unknown schedule type: {schedule.schedule_type}"
                    )
                    continue

                scheduler.add_job(
                    func=create_job_wrapper(job_func, schedule.id, app),
                    trigger=trigger,
                    id=f"{schedule.module}-{schedule.id}",
                    replace_existing=True,
                )
        except Exception as e:
            postarr_logger.error(f"Error loading schedules: {e}")


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
                        if Settings.TIME_FORMAT.value == "24":
                            schedule.next_run = next_run.strftime("%b %d, %Y %H:%M")
                        else:
                            schedule.next_run = next_run.strftime("%b %d, %Y %I:%M %p")
                    else:
                        schedule.next_run = "Pending"
                else:
                    schedule.next_run = "N/A"
            db.session.commit()
        except Exception as e:
            postarr_logger.error(f"Error updating next run times: {e}")


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
            version = os.getenv("VERSION", "0.0.1")
            postarr_logger.info(f"Starting Postarr v{version}")
            postarr_logger.info("Initializing database schema...")
            with db.engine.connect() as conn:
                conn.execute(db.text("PRAGMA journal_mode=WAL;"))
            postarr_logger.info("WAL mode enabled for SQLite database")
            load_schedules_from_db(app)
            if not scheduler.running:
                scheduler.start()
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

            postarr_logger.debug("Poster Renamerr Payload:")
            postarr_logger.debug(pformat(poster_renamer_payload))

            job_id = progress_instance.add_job(job_name=Settings.POSTER_RENAMERR.value)
            postarr_logger.info(f"Job Poster Renamerr: '{job_id}' added.")

            renamer = PosterRenamerr(poster_renamer_payload)

            def check_borders() -> bool:
                from postarr.utils.database import Database

                with app.app_context():
                    db_instance = Database(db, postarr_logger)
                    first_file_settings = db_instance.get_first_file_settings()
                    if not first_file_settings:
                        return False
                    return (
                        first_file_settings.get("border_setting")
                        != poster_renamer_payload.border_setting
                        or first_file_settings.get("custom_color")
                        != poster_renamer_payload.custom_color
                    )

            def remove_job():
                try:
                    progress_instance(job_id, 100, ProgressState.COMPLETED)
                except Exception as e:
                    postarr_logger.error(f"Error removing job '{job_id}': {e}")
                finally:
                    sleep(2)
                    progress_instance.remove_job(job_id)
                    postarr_logger.info(
                        f"Poster Renamerr Job: '{job_id}' has been removed"
                    )

            def run_renamerr_callback(fut):
                try:
                    postarr_logger.info("Renamerr task completed")
                    media_dict = fut.result()
                    if poster_renamer_payload.unmatched_assets:
                        unmatched_future = executor.submit(
                            handle_unmatched_assets_task,
                            app,
                            radarr,
                            sonarr,
                            plex,
                            chained=True,
                        )
                        if poster_renamer_payload.upload_to_plex:
                            unmatched_future.add_done_callback(
                                lambda fut: run_unmatched_after_renamerr_callback(
                                    media_dict, fut
                                )
                            )
                        else:
                            remove_job()

                    elif poster_renamer_payload.upload_to_plex:
                        if media_dict:
                            postarr_logger.debug(
                                f"Media dict from renamer: {media_dict}"
                            )
                        else:
                            postarr_logger.warning(
                                "No media dict from renamer. Proceeding with full upload."
                            )
                        plex_upload_future = executor.submit(
                            handle_plex_uploaderr_task,
                            app,
                            plex,
                            radarr,
                            sonarr,
                            webhook_item,
                            media_dict,
                            chained=True,
                        )
                        plex_upload_future.add_done_callback(run_plex_upload_callback)
                    else:
                        remove_job()

                except Exception as e:
                    postarr_logger.error(f"Error in plex upload callback: {e}")

            def run_border_replacerr_callback(fut):
                try:
                    postarr_logger.info("Border replacerr task completed.")
                    renamer_future = executor.submit(
                        renamer.run, progress_instance, job_id
                    )
                    renamer_future.add_done_callback(run_renamerr_callback)
                except Exception as e:
                    postarr_logger.error(f"Error in run_border_replacerr_callback: {e}")

            def run_unmatched_after_renamerr_callback(media_dict, fut):
                try:
                    postarr_logger.info("Unmatched assets task completed.")
                    if media_dict:
                        postarr_logger.debug(f"Media dict from renamer: {media_dict}")
                    else:
                        postarr_logger.warning(
                            "No media dict from renamer. Proceeding with full upload."
                        )
                    plex_upload_future = executor.submit(
                        handle_plex_uploaderr_task,
                        app,
                        plex,
                        radarr,
                        sonarr,
                        webhook_item,
                        media_dict,
                        chained=True,
                    )
                    plex_upload_future.add_done_callback(run_plex_upload_callback)
                except Exception as e:
                    postarr_logger.error(
                        f"Error in run_unmatched_after_renamerr_callback: {e}"
                    )

            def run_plex_upload_callback(fut):
                postarr_logger.info("Plex uploaderr task completed.")
                remove_job()

            def run_unmatched_assets_only_unmatched_callback(fut):
                try:
                    postarr_logger.info("Unmatched assets task completed.")
                    if check_borders():
                        border_replacerr_future = executor.submit(
                            run_border_replacer_task, app
                        )
                        border_replacerr_future.add_done_callback(
                            run_border_replacerr_callback
                        )
                    else:
                        renamer_future = executor.submit(
                            renamer.run, progress_instance, job_id
                        )
                        renamer_future.add_done_callback(run_renamerr_callback)
                except Exception as e:
                    postarr_logger.error(
                        f"Error in run_unmatched_assets_only_unmatched_callback: {e}"
                    )

            def run_drive_sync_callback(fut):
                try:
                    postarr_logger.info("Drive sync task completed.")
                    if (
                        poster_renamer_payload.unmatched_assets
                        and poster_renamer_payload.only_unmatched
                    ):
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
                        renamer_future = executor.submit(
                            renamer.run, progress_instance, job_id
                        )
                        renamer_future.add_done_callback(run_renamerr_callback)
                except Exception as e:
                    postarr_logger.error(f"Error in run_drive_sync_callback: {e}")

            if webhook_item:
                postarr_logger.debug("Submitting webhook task to thread pool")
                future = executor.submit(
                    renamer.run,
                    progress_instance,
                    job_id,
                    webhook_item,
                )
                future.add_done_callback(run_renamerr_callback)
            else:
                if poster_renamer_payload.drive_sync:
                    postarr_logger.info("Starting drive sync task before renamer...")
                    drive_sync_future = executor.submit(
                        run_drive_sync_task, app, chained=True
                    )
                    drive_sync_future.add_done_callback(run_drive_sync_callback)
                elif (
                    poster_renamer_payload.unmatched_assets
                    and poster_renamer_payload.only_unmatched
                ):
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
                    renamer_future = executor.submit(
                        renamer.run, progress_instance, job_id
                    )
                    renamer_future.add_done_callback(run_renamerr_callback)

            postarr_logger.debug("Returning response: Poster renamer task started")
            return {
                "message": "Poster renamer task started",
                "job_id": job_id,
                "success": True,
            }
        except Exception as e:
            postarr_logger.error(f"Error in Poster Renamer Task: {str(e)}")
            return {"success": False, "message": str(e)}


def run_border_replacer_task(
    app, overrides: dict | None = None, chained: bool = False
) -> dict:
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
                    postarr_logger.error(f"Error removing job '{job_id}': {e}")
                finally:
                    sleep(2)
                    progress_instance.remove_job(job_id)
                    postarr_logger.info(
                        f"Border Replacer Job: '{job_id}' has been removed"
                    )

            if first_file_settings:
                current_border_setting = first_file_settings.get("border_setting")
                current_custom_color = first_file_settings.get("custom_color")

                if (
                    current_border_setting == border_setting
                    and current_custom_color == custom_color
                ):
                    postarr_logger.info(
                        "Skipping task: Border and color settings already applied to files."
                    )
                    return {
                        "message": "Border and color settings already applied. Task skipped.",
                        "success": True,
                        "job_id": None,
                    }

            job_id = progress_instance.add_job(Settings.BORDER_REPLACERR.value)
            postarr_logger.debug(f"Job Border Replacerr: '{job_id}' added.")
            postarr_logger.debug("Border Replacerr Payload:")
            postarr_logger.debug(pformat(border_replacerr_payload))
            border_replacerr = BorderReplacerr(payload=border_replacerr_payload)
            if chained:
                border_replacerr.replace_current_assets(progress_instance, job_id)
                progress_instance.remove_job(job_id)
                postarr_logger.info(f"Border Replacer Job: '{job_id}' has been removed")
            else:
                postarr_logger.debug("Submitting border replacerr task to thread pool")
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
        postarr_logger.error(f"Error in Border Replacer Task: {str(e)}")
        return {"success": False, "message": str(e)}


def handle_unmatched_assets_task(
    app, radarr, sonarr, plex, overrides: dict | None = None, chained: bool = False
) -> dict:
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

            postarr_logger.debug("Unmatched Assets Payload:")
            postarr_logger.debug(pformat(unmatched_assets_payload))
            job_id = progress_instance.add_job(Settings.UNMATCHED_ASSETS.value)
            postarr_logger.info(f"Job Unmatched Assets: '{job_id}' added.")
            unmatched_assets = UnmatchedAssets(unmatched_assets_payload)

            def remove_job_cb(fut):
                try:
                    fut.result()
                except Exception as e:
                    postarr_logger.error(f"Error removing job '{job_id}': {e}")
                finally:
                    sleep(2)
                    progress_instance.remove_job(job_id)
                    postarr_logger.info(
                        f"Unmatched Assets Job: '{job_id}' has been removed"
                    )

            if chained:
                unmatched_assets.run(progress_instance, job_id)
                progress_instance.remove_job(job_id)
                postarr_logger.info(
                    f"Unmatched Assets Job: '{job_id}' has been removed"
                )
            else:
                postarr_logger.debug("Submitting unmatched assets task to thread pool")
                future = executor.submit(
                    unmatched_assets.run,
                    progress_instance,
                    job_id,
                )
                postarr_logger.debug("Task submitted successfully")
                future.add_done_callback(remove_job_cb)

            return {
                "message": "Unmatched assets task started",
                "job_id": job_id,
                "success": True,
            }

    except Exception as e:
        postarr_logger.error(f"Error in Unmatched Assets Task: {str(e)}")
        postarr_logger.error(traceback.format_exc())
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

        postarr_logger.debug("Plex Uploaderr Payload:")
        postarr_logger.debug(pformat(plex_uploader_payload))

        job_id = progress_instance.add_job(Settings.PLEX_UPLOADERR.value)
        postarr_logger.info(f"Job Plex Uploaderr: '{job_id}' added.")

        def remove_job_cb(fut):
            try:
                fut.result()
            except Exception as e:
                postarr_logger.debug(f"Error removing job '{job_id}': {e}")
            finally:
                sleep(2)
                progress_instance.remove_job(job_id)
                postarr_logger.info(f"Plex uploaderr: '{job_id}' has been removed")

        if webhook_item and media_dict:
            plex_uploaderr = PlexUploaderr(
                plex_uploader_payload,
                webhook_item=webhook_item,
                media_dict=media_dict,
            )
            postarr_logger.debug(
                "Submitting webhook plex uploaderr task to thread pool"
            )
            future = executor.submit(plex_uploaderr.upload_posters_webhook, job_id)
            postarr_logger.debug("Task submitted successfully")
        else:
            plex_uploaderr = PlexUploaderr(plex_uploader_payload)

            if chained:
                plex_uploaderr.upload_posters_full(progress_instance, job_id)
                progress_instance.remove_job(job_id)
                postarr_logger.info(f"Plex uploaderr: '{job_id}' has been removed")
            else:
                postarr_logger.debug("Submitting plex uploaderr task to thread pool")
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
        return {"success": False, "message": str(e)}


def run_drive_sync_task(
    app, overrides: dict | None = None, chained: bool = False
) -> dict:
    with app.app_context():
        postarr_logger.info(f"run_drive_sync_task called with chained={chained}")
        payload = webui_utils.create_drive_sync_payload()
        if overrides:
            if "logLevel" in overrides:
                log_level_str = overrides["logLevel"].upper()
                log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
                payload.log_level = log_level
        postarr_logger.debug("Drive Sync Payload:")
        postarr_logger.debug(pformat(payload))
        job_id = progress_instance.add_job(Settings.DRIVE_SYNC.value)
        postarr_logger.info(f"Job Drive Sync: '{job_id}' added.")
        drive_sync = DriveSync(payload)

        def remove_job_cb(fut):
            try:
                fut.result()
                progress_instance(job_id, 100, ProgressState.COMPLETED)
            except Exception as e:
                postarr_logger.debug(f"Error removing job '{job_id}': {e}")
            finally:
                sleep(2)
                progress_instance.remove_job(job_id)
                postarr_logger.info(f"Drive Sync: '{job_id}' has been removed")

        if chained:
            try:
                drive_sync.sync_all_drives(progress_instance, job_id)
                progress_instance.remove_job(job_id)
                postarr_logger.info(f"Drive Sync: '{job_id}' has been removed")
            except Exception as e:
                postarr_logger.error(f"Drive sync failed: {e}")
        else:
            future = executor.submit(
                drive_sync.sync_all_drives, progress_instance, job_id
            )
            future.add_done_callback(remove_job_cb)

        return {
            "message": "Drive Sync task started",
            "job_id": job_id,
            "success": True,
        }


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
