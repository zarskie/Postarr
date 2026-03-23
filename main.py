import datetime
import logging
import os
import threading
import time
from logging import Logger
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from modules import PosterRenamerr, UnmatchedAssets, YamlConfig
from modules.database_cache import Database
from modules.logger import init_logger
from modules.plex_upload import PlexUploaderr
from modules.settings import Settings
from modules.utils import construct_schedule_time, parse_schedule_string

log_level_env = os.getenv("MAIN_LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_env, logging.INFO)
log_dir = Path(Settings.LOG_DIR.value) / Settings.MAIN.value
logger = logging.getLogger("Main")
init_logger(logger, log_dir, "main", log_level=log_level)
logger.info(f"LOG LEVEL: {log_level_env}")
db = Database(logger)


def start_cli_listener():
    from modules.webhook_listener import cli_app

    cli_app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)


def get_config(logger: Logger):
    config = YamlConfig(logger)
    return config


def run_renamer(config: YamlConfig, webhook_item: dict | None = None):
    payload = config.create_poster_renamer_payload()
    renamerr = PosterRenamerr(payload)

    if webhook_item:
        logger.info("Poster renamerr triggered on webhook item")
        media_dict = renamerr.run(single_item=webhook_item)
        if payload.upload_to_plex and media_dict:
            run_plex_uploaderr(
                config,
                webhook_item,
                media_dict,
            )
    else:
        renamerr.run()
        if payload.upload_to_plex:
            run_plex_uploaderr(config)
    logger.info("Finished poster renamerr")
    if payload.unmatched_assets:
        run_unmatched_assets(config)


def run_unmatched_assets(config: YamlConfig):
    payload = config.create_unmatched_assets_payload()
    unmatched_assets = UnmatchedAssets(payload)
    logger.info("Running unmatched assets")
    unmatched_assets.run()
    logger.info("Finished unmatched assets")


def run_plex_uploaderr(
    config: YamlConfig,
    webhook_item: dict | None = None,
    media_dict: dict | None = None,
):
    payload = config.create_plex_uploaderr_payload()
    plex_uploaderr = PlexUploaderr(
        payload,
        webhook_item,
        media_dict,
    )
    if webhook_item and media_dict:
        logger.info("Running plex uploaderr for webhook run.")
        plex_uploaderr.upload_posters_webhook()
        logger.info("Finished plex uploaderr.")
    else:
        logger.info("Running plex uploaderr for full library.")
        plex_uploaderr.upload_posters_full()
        logger.info("Finished plex uploaderr.")


def add_scheduled_jobs(scheduler: BackgroundScheduler, config: YamlConfig):
    def add_job_safe(func, job_id, schedule, schedule_name):
        if not schedule:
            logger.warning(f"No schedule found for {schedule_name}. Skipping Job")
            return
        if schedule.lower() == "run":
            logger.info(
                f"Schedule for '{schedule_name}' is set to 'run'. Running job immediately."
            )
            try:
                func(config)
                logger.info(f"Job '{schedule_name}' executed successfully")
            except Exception as e:
                logger.error(f"Error executing job '{schedule_name}': {e}")
            return
        try:
            parsed_schedules = parse_schedule_string(schedule, logger)
            for i, parsed_schedule in enumerate(parsed_schedules):
                schedule_time = construct_schedule_time(parsed_schedule)

                unique_job_id = f"{job_id}_{i}"
                scheduler.add_job(
                    func,
                    "cron",
                    **parsed_schedule,
                    args=[config],
                    id=unique_job_id,
                    replace_existing=True,
                    misfire_grace_time=10,
                )
                logger.info(f"Scheduled job '{job_id}' {schedule_time}")
        except ValueError as e:
            logger.error(f"Failed to schedule job '{job_id}' for {schedule_name}: {e}")

    job_configs = {
        "run_renamer": {
            "schedule": config.schedule_config.get(Settings.POSTER_RENAMERR.value),
            "function": run_renamer,
            "name": Settings.POSTER_RENAMERR.value,
        },
        "run_unmatched_assets": {
            "schedule": config.schedule_config.get(Settings.UNMATCHED_ASSETS.value),
            "function": run_unmatched_assets,
            "name": Settings.UNMATCHED_ASSETS.value,
        },
        "run_plex_uploader": {
            "schedule": config.schedule_config.get(Settings.PLEX_UPLOADERR.value),
            "function": run_plex_uploaderr,
            "name": Settings.PLEX_UPLOADERR.value,
        },
    }

    for job_id, job_config in job_configs.items():
        add_job_safe(
            job_config["function"],
            job_id,
            job_config["schedule"],
            job_config["name"],
        )


def run_cli():
    config = get_config(logger)
    run_single_item = config.get_run_single_item()
    if run_single_item:
        webhook_thread = threading.Thread(target=start_cli_listener, daemon=True)
        webhook_thread.start()

    scheduler = BackgroundScheduler()
    add_scheduled_jobs(scheduler, config)
    scheduler.start()
    try:
        while True:
            next_run = min(
                (
                    job.next_run_time
                    for job in scheduler.get_jobs()
                    if job.next_run_time
                ),
                default=None,
            )
            if next_run:
                now = datetime.datetime.now(next_run.tzinfo)
                total_sleep_time = max(1, (next_run - now).total_seconds())
                logger.debug(
                    f"Sleeping for {total_sleep_time:.2f} seconds until next job"
                )
            else:
                total_sleep_time = 60
            slept_time = 0
            while slept_time < total_sleep_time:
                time.sleep(min(1, total_sleep_time, slept_time))
                slept_time += 1
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down CLI application")
        scheduler.shutdown()


if __name__ == "__main__":
    run_cli()
    # run_unmatched_assets()
