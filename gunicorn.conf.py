import os

# accesslog = "/config/logs/web-ui/web_ui_debug.log"
# errorlog = "/config/logs/web-ui/web_ui_debug.log"
# loglevel = "debug"


def on_starting(server):
    from daps_webui import app, daps_logger, db

    with app.app_context():
        version = os.getenv("VERSION", "0.0.1")
        daps_logger.info(f"Starting daps-ui v{version}")
        daps_logger.info("Initializing database schema...")
        db.create_all()
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA journal_mode=WAL;"))
        daps_logger.info("WAL mode enabled for SQLite database")


def post_worker_init(worker):
    """Start scheduler in the single worker"""
    from daps_webui import (
        app,
        daps_logger,
        load_schedules_from_db,
        scheduler,
        update_next_run_times,
    )

    with app.app_context():
        daps_logger.info(f"Starting scheduler in worker {worker.pid}")
        load_schedules_from_db(app)
        scheduler.start()
        daps_logger.info(f"Scheduler started successfully in worker {worker.pid}")
        update_next_run_times(app)
