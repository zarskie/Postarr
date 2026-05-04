import os


def on_starting(server):
    from postarr import app, db, postarr_logger

    with app.app_context():
        version = os.getenv("VERSION", "dev")
        postarr_logger.info(f"Starting Postarr v{version}")
        postarr_logger.info("Initializing database schema...")
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA journal_mode=WAL;"))
        postarr_logger.info("WAL mode enabled for SQLite database")


def post_worker_init(worker):
    """Start scheduler in the single worker"""
    from postarr import (
        app,
        load_schedules_from_db,
        postarr_logger,
        scheduler,
        update_next_run_times,
    )

    with app.app_context():
        postarr_logger.debug(f"Starting scheduler in worker {worker.pid}")
        load_schedules_from_db(app)
        scheduler.start()
        postarr_logger.debug(f"Scheduler started successfully in worker {worker.pid}")
        update_next_run_times(app)
