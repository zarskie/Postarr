import os
from datetime import datetime
from logging import Logger

import pytz
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from postarr.models.file_cache import FileCache
from postarr.models.jobs import CurrentJobs, JobHistory


class Database:
    def __init__(self, db, logger: Logger):
        self.logger = logger
        self.db = db

    def delete_file_cache_entry(self, file_path: str) -> bool:
        try:
            entry = (
                self.db.session.query(FileCache).filter_by(file_path=file_path).first()
            )
            if entry:
                self.db.session.delete(entry)
                self.db.session.commit()
                self.logger.debug(f"Deleted poster: {file_path} from database")
                return True
            return False
        except SQLAlchemyError as e:
            self.logger.error(f"Error deleting file cache entry: {e}")
            self.db.session.rollback()
            return False

    def get_first_file_settings(self) -> dict | None:
        try:
            first_entry = self.db.session.query(FileCache).first()
            if first_entry:
                self.logger.debug(
                    f"Found first file in file cache: {first_entry.file_path}"
                )
                return {
                    "border_setting": first_entry.border_setting,
                    "custom_color": first_entry.custom_color,
                }
            self.logger.debug("No files found in file cache")
            return None
        except SQLAlchemyError as e:
            self.logger.error(f"Error querying file cache: {e}")

    def update_scheduled_job(
        self, job_name: str, next_run: datetime | None = None
    ) -> None:
        try:
            first_entry = (
                self.db.session.query(JobHistory)
                .filter_by(job_name=job_name)
                .order_by(desc(JobHistory.run_time))
                .first()
            )
            last_run = first_entry.run_time if first_entry else None

            job = (
                self.db.session.query(CurrentJobs).filter_by(job_name=job_name).first()
            )
            if job:
                job.last_run = last_run

                if next_run is None:
                    next_run = job.next_run

                job.next_run = next_run
            else:
                job = CurrentJobs(
                    job_name=job_name,
                    last_run=last_run,
                    next_run=next_run,
                )
                self.db.session.add(job)
                self.logger.debug(f"Added new job: {job_name}")

            self.db.session.commit()

        except SQLAlchemyError as e:
            self.logger.error(f"Error updating job history: {e}")
            self.db.session.rollback()

    def add_job_to_history(self, job_name: str, status: str, run_type: str) -> None:
        try:
            docker_timezone = os.getenv("TZ", "UTC")
            local_tz = pytz.timezone(docker_timezone)

            current_time = datetime.now(local_tz)

            new_entry = JobHistory(
                job_name=job_name,
                run_time=current_time,
                status=status,
                run_type=run_type,
            )
            self.db.session.add(new_entry)
            self.db.session.commit()
            self._prune_old_job_entries(job_name)
            self.logger.debug(
                f"Added job history entry for: {job_name} at {current_time}"
            )

        except SQLAlchemyError as e:
            self.logger.error(f"Error adding job to history: {e}")
            self.db.session.rollback()

    def clear_scheduled_job(self, job_name: str) -> None:
        try:
            job = (
                self.db.session.query(CurrentJobs).filter_by(job_name=job_name).first()
            )
            if job:
                job.next_run = None
                self.db.session.commit()
                self.logger.info(f"Cleared next run time for job: {job_name}")
            else:
                self.logger.warning(
                    f"Tried to clear next run for job '{job_name}', but no entry found."
                )
        except SQLAlchemyError as e:
            self.logger.error(f"Error clearing scheduled job '{job_name}': {e}")
            self.db.session.rollback()

    def _prune_old_job_entries(self, job_name: str) -> None:
        try:
            job_entries_subquery = (
                select(JobHistory.id)
                .filter_by(job_name=job_name)
                .order_by(desc(JobHistory.run_time))
                .limit(10)
            )
            deleted_count = (
                self.db.session.query(JobHistory)
                .filter(
                    JobHistory.job_name == job_name,
                    ~JobHistory.id.in_(job_entries_subquery),
                )
                .delete(synchronize_session=False)
            )
            if deleted_count:
                self.logger.debug(
                    f"Pruned {deleted_count} old job entries for {job_name}"
                )

            self.db.session.commit()
        except SQLAlchemyError as e:
            self.logger.error(f"Error pruning old job history: {e}")
            self.db.session.rollback()
