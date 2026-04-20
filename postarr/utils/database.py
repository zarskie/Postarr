# pyright: reportCallIssue=false
import os
from datetime import datetime
from logging import Logger

import pytz
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from postarr import models


class Database:
    def __init__(self, db, logger: Logger):
        self.logger = logger
        self.db = db

    def delete_file_cache_entry(self, file_path: str) -> bool:
        try:
            entry = (
                self.db.session.query(models.FileCache)
                .filter_by(file_path=file_path)
                .first()
            )
            if entry:
                self.db.session.delete(entry)
                self.db.session.commit()
                self.logger.debug("Deleted poster: %s from database", file_path)
                return True
            return False
        except SQLAlchemyError as e:
            self.logger.error("Error deleting file cache entry: %s", e)
            self.db.session.rollback()
            return False

    def add_unmatched_item(
        self,
        item_type: str,
        title: str,
        arr_id: int,
        instance: str,
        imdb_id: str | None = None,
        tmdb_id: str | None = None,
        tvdb_id: str | None = None,
        main_poster_missing: bool = True,
        season_number: int | None = None,
    ) -> bool:
        try:
            if item_type == "movie":
                existing = models.UnmatchedMovies.query.filter_by(title=title).first()
                if existing is None:
                    item = models.UnmatchedMovies(
                        title=title,
                        arr_id=arr_id,
                        instance=instance,
                        imdb_id=imdb_id,
                        tmdb_id=tmdb_id,
                    )
                    self.db.session.add(item)
                else:
                    existing.arr_id = arr_id
                    existing.instance = instance
                    existing.imdb_id = imdb_id
                    existing.tmdb_id = tmdb_id
            elif item_type == "show" or item_type == "season":
                existing = models.UnmatchedShows.query.filter_by(title=title).first()
                if existing is None:
                    show = models.UnmatchedShows(
                        title=title,
                        arr_id=arr_id,
                        main_poster_missing=int(main_poster_missing),
                        instance=instance,
                        imdb_id=imdb_id,
                        tmdb_id=tmdb_id,
                        tvdb_id=tvdb_id,
                    )
                    self.db.session.add(show)
                    self.db.session.flush()
                    existing = show
                else:
                    if main_poster_missing and not existing.main_poster_missing:
                        existing.main_poster_missing = 1
                if season_number is not None:
                    season_str = f"season{int(season_number):02d}"
                    existing_season = models.UnmatchedSeasons.query.filter_by(
                        show_id=existing.id, season=season_str
                    ).first()
                    if existing_season is None:
                        season = models.UnmatchedSeasons(
                            show_id=existing.id,
                            season=season_str,
                        )
                        self.db.session.add(season)

            elif item_type == "collection":
                existing = models.UnmatchedCollections.query.filter_by(
                    title=title
                ).first()
                if existing is None:
                    item = models.UnmatchedCollections(title=title)
                    self.db.session.add(item)
            else:
                self.logger.error("Unknown item_type: %s", item_type)
                return False

            self.db.session.commit()
            return True

        except SQLAlchemyError as e:
            self.logger.error("Error adding unmatched item: %s", e)
            self.db.session.rollback()
            return False

    def get_first_file_settings(self) -> dict | None:
        try:
            first_entry = self.db.session.query(models.FileCache).first()
            if first_entry:
                return {
                    "border_setting": first_entry.border_setting,
                    "custom_color": first_entry.custom_color,
                }
            self.logger.debug("No files found in file cache")
            return None
        except SQLAlchemyError as e:
            self.logger.error("Error querying file cache: %s", e)

    def update_scheduled_job(
        self, job_name: str, next_run: datetime | None = None
    ) -> None:
        try:
            first_entry = (
                self.db.session.query(models.JobHistory)
                .filter_by(job_name=job_name)
                .order_by(desc(models.JobHistory.run_time))
                .first()
            )
            last_run = first_entry.run_time if first_entry else None

            job = (
                self.db.session.query(models.CurrentJobs)
                .filter_by(job_name=job_name)
                .first()
            )
            if job:
                job.last_run = last_run

                if next_run is None:
                    next_run = job.next_run

                job.next_run = next_run
            else:
                job = models.CurrentJobs(
                    job_name=job_name,
                    last_run=last_run,
                    next_run=next_run,
                )
                self.db.session.add(job)
                self.logger.debug("Added new job: %s", job_name)

            self.db.session.commit()

        except SQLAlchemyError as e:
            self.logger.error("Error updating job history: %s", e)
            self.db.session.rollback()

    def add_job_to_history(
        self,
        job_id: str,
        job_name: str,
        status: str,
        run_type: str,
        message: str | None = None,
    ) -> None:
        try:
            docker_timezone = os.getenv("TZ", "UTC")
            local_tz = pytz.timezone(docker_timezone)

            current_time = datetime.now(local_tz)

            new_entry = models.JobHistory(
                job_id=job_id,
                job_name=job_name,
                run_time=current_time,
                status=status,
                run_type=run_type,
                message=message,
            )
            self.db.session.add(new_entry)
            self.db.session.commit()
            self._prune_old_job_entries(job_name)
            self.logger.debug(
                "Added job history entry for: %s at %s", job_id, current_time
            )
            self.logger.trace(  # type: ignore[attr-defined]
                "Job history entry: job_id: %s, job_name: %s, run_time: %s, status: %s, run_type: %s, message: %s",
                job_id,
                job_name,
                current_time,
                status,
                run_type,
                message,
            )

        except SQLAlchemyError as e:
            self.logger.error("Error adding job to history: %s", e)
            self.db.session.rollback()

    def _prune_old_job_entries(self, job_name: str) -> None:
        try:
            job_entries_subquery = (
                select(models.JobHistory.job_name)
                .filter_by(job_name=job_name)
                .order_by(desc(models.JobHistory.run_time))
                .limit(10)
            )
            deleted_count = (
                self.db.session.query(models.JobHistory)
                .filter(
                    models.JobHistory.job_name == job_name,
                    ~models.JobHistory.id.in_(job_entries_subquery),
                )
                .delete(synchronize_session=False)
            )
            if deleted_count:
                self.logger.trace(  # type: ignore[attr-defined]
                    "Pruned %s old job entries for %s", deleted_count, job_name
                )

            self.db.session.commit()
        except SQLAlchemyError as e:
            self.logger.error("Error pruning old job history: %s", e)
            self.db.session.rollback()
