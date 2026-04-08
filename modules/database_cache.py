import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from logging import Logger
from pathlib import Path

from modules.settings import Settings


class Database:
    def __init__(self, logger: Logger) -> None:
        self.initialize_db()
        self.logger = logger

    def get_db_connection(self):
        conn = sqlite3.connect(Settings.DB_PATH.value)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize_db(self):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS file_cache (
                    file_path TEXT NOT NULL PRIMARY KEY,
                    file_name TEXT,
                    status TEXT,
                    has_episodes INTEGER,
                    has_file INTEGER,
                    media_type TEXT, 
                    file_hash TEXT,
                    original_file_hash TEXT,
                    source_path TEXT,
                    border_replaced INTEGER NOT NULL DEFAULT 0,
                    border_setting TEXT,
                    custom_color TEXT,
                    webhook_run INTEGER,
                    uploaded_to_libraries TEXT NOT NULL DEFAULT '[]',
                    uploaded_editions TEXT NOT NULL DEFAULT '[]',
                    instance TEXT,
                    arr_id INTEGER,
                    tmdb_id TEXT,
                    imdb_id TEXT,
                    tvdb_id TEXT
                )
                """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS unmatched_movies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT UNIQUE NOT NULL,
                        arr_id INTEGER,
                        instance TEXT,
                        imdb_id TEXT,
                        tmdb_id TEXT,
                        is_missing INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS unmatched_collections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT UNIQUE NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS unmatched_shows (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT UNIQUE NOT NULL,
                        arr_id INTEGER,
                        main_poster_missing INTEGER NOT NULL DEFAULT 0,
                        instance TEXT,
                        imdb_id TEXT,
                        tmdb_id TEXT,
                        tvdb_id TEXT,
                        is_missing INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS unmatched_seasons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        show_id INTEGER NOT NULL,
                        season TEXT NOT NULL,
                        is_missing INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (show_id) REFERENCES unmatched_shows (id) ON DELETE CASCADE,
                        UNIQUE (show_id, season)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS unmatched_stats (
                    id INTEGER PRIMARY KEY,
                    total_collections INTEGER NOT NULL DEFAULT 0,
                    total_movies_all INTEGER NOT NULL DEFAULT 0,
                    total_series_all INTEGER NOT NULL DEFAULT 0,
                    total_seasons_all INTEGER NOT NULL DEFAULT 0,
                    total_movies_with_file INTEGER NOT NULL DEFAULT 0,
                    total_series_with_episodes INTEGER NOT NULL DEFAULT 0,
                    total_seasons_with_episodes INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
                conn.commit()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS webhook_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_type TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT unique_item_type_name UNIQUE (item_type, item_name)
                    )
                    """
                )
                conn.commit()

    def add_file(
        self,
        file_path: str,
        file_name: str,
        status: str | None,
        has_episodes: bool | None,
        has_file: bool | None,
        media_type: str,
        file_hash: str,
        original_file_hash: str,
        source_path: str,
        border_replaced: bool,
        border_setting: str | None = None,
        custom_color: str | None = None,
        webhook_run: bool | None = None,
        instance: str | None = None,
        arr_id: int | None = None,
        tmdb_id: str | None = None,
        imdb_id: str | None = None,
        tvdb_id: str | None = None,
    ) -> None:
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "SELECT 1 FROM file_cache WHERE file_path = ?",
                        (file_path,),
                    )
                    row_exists = cursor.fetchone() is not None
                    sql_query = """
                        INSERT OR REPLACE INTO file_cache (
                            file_path, file_name, status, has_episodes, has_file, media_type,
                            file_hash, original_file_hash, source_path, border_replaced,
                            border_setting, custom_color, webhook_run,
                            uploaded_to_libraries, uploaded_editions, instance, arr_id, tmdb_id, imdb_id, tvdb_id
                        ) VALUES (
                            :file_path, :file_name, :status, :has_episodes, :has_file, :media_type, :file_hash, :original_file_hash, :source_path, :border_replaced, :border_setting, :custom_color, :webhook_run, :uploaded_to_libraries, :uploaded_editions, :instance, :arr_id, :tmdb_id, :imdb_id, :tvdb_id
                        )
                    """
                    values = {
                        "file_path": file_path,
                        "file_name": file_name,
                        "status": status,
                        "has_episodes": has_episodes,
                        "has_file": has_file,
                        "media_type": media_type,
                        "file_hash": file_hash,
                        "original_file_hash": original_file_hash,
                        "source_path": source_path,
                        "border_replaced": int(border_replaced),
                        "border_setting": border_setting,
                        "custom_color": custom_color,
                        "webhook_run": webhook_run,
                        "uploaded_to_libraries": json.dumps([]),
                        "uploaded_editions": json.dumps([]),
                        "instance": instance,
                        "arr_id": arr_id,
                        "tmdb_id": tmdb_id,
                        "imdb_id": imdb_id,
                        "tvdb_id": tvdb_id,
                    }
                    # self.logger.debug(f"Executing SQL: {sql_query}")
                    # self.logger.debug(f"Values: {values}")
                    cursor.execute(sql_query, values)
                    conn.commit()
                    if row_exists:
                        self.logger.info(
                            f"File '{file_path}' was successfully updated in file cache."
                        )
                    else:
                        self.logger.debug(
                            f"File '{file_path}' was successfully added to file cache."
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to add file '{file_path}' to database: {e}"
                    )

    def is_duplicate_webhook(self, new_item, cache_duration=600) -> bool:
        item_name = Path(new_item["item_path"]).stem
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=cache_duration)

        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "DELETE FROM webhook_cache WHERE timestamp < ?", (cutoff,)
                    )
                    expired_count = cursor.rowcount
                    self.logger.debug(f"Expired webhooks removed: {expired_count}")

                    cursor.execute(
                        "SELECT 1 FROM webhook_cache WHERE item_type = ? AND item_name = ?",
                        (
                            new_item["type"],
                            item_name,
                        ),
                    )
                    if cursor.fetchone():
                        self.logger.debug(f"Duplicate webhook detected: {item_name}")
                        return True

                    cursor.execute(
                        "INSERT INTO webhook_cache (item_type, item_name, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        (new_item["type"], item_name),
                    )
                    self.logger.debug(f"New webhook added to cache: {item_name}")
                    conn.commit()

                except sqlite3.InternalError as e:
                    self.logger.debug(f"IntegrityError: {e}")
                    return True
        return False

    def update_file(
        self,
        file_hash: str,
        original_file_hash: str,
        source_path: str,
        file_path: str,
        border_replaced: bool,
        border_setting: str | None = None,
        custom_color: str | None = None,
    ) -> None:
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET file_hash = ?, original_file_hash = ?, source_path = ?, border_replaced = ?, border_setting = ?, custom_color = ?, uploaded_to_libraries = ?, uploaded_editions = ? WHERE file_path = ?",
                        (
                            file_hash,
                            original_file_hash,
                            source_path,
                            int(border_replaced),
                            border_setting,
                            custom_color,
                            json.dumps([]),
                            json.dumps([]),
                            file_path,
                        ),
                    )
                    conn.commit()
                    self.logger.debug(
                        f"File '{file_path}' was successfully updated in file cache."
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update file '{file_path}' to database: {e}"
                    )

    def update_border_replaced_hash(
        self,
        file_path: str,
        file_hash: str,
        border_replaced: bool,
        border_setting: str,
        custom_color: str | None = None,
    ):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET file_hash = ?, border_replaced = ?, border_setting = ?, custom_color = ?, uploaded_to_libraries = ?, uploaded_editions = ? WHERE file_path = ?",
                        (
                            file_hash,
                            border_replaced,
                            border_setting,
                            custom_color,
                            json.dumps([]),
                            json.dumps([]),
                            file_path,
                        ),
                    )
                    conn.commit()
                    self.logger.debug(
                        f"File '{file_path}' was successfully updated in file cache."
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update file '{file_path}' to database {e}"
                    )

    def update_status(self, file_path: str, status: str):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET status = ? WHERE file_path = ?",
                        (
                            status,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'status' to {status} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'status' for {file_path}: {e}"
                    )

    def update_has_episodes(self, file_path: str, has_episodes: bool):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET has_episodes = ? WHERE file_path = ?",
                        (
                            int(has_episodes),
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'has_episodes' to {has_episodes} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'has_episodes' for {file_path}: {e}"
                    )

    def update_has_file(self, file_path: str, has_file: bool):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET has_file = ? WHERE file_path = ?",
                        (
                            int(has_file),
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'has_file' to {has_file} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'has_file' for {file_path}: {e}"
                    )

    def update_uploaded_to_libraries(self, file_path: str, new_libraries: list):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "SELECT uploaded_to_libraries FROM file_cache WHERE file_path = ?",
                        (file_path,),
                    )
                    result = cursor.fetchone()
                    if not result:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped"
                        )
                        return
                    current_libraries = json.loads(result[0]) if result[0] else []
                    updated_libraries = list(set(current_libraries + new_libraries))
                    cursor.execute(
                        "UPDATE file_cache SET uploaded_to_libraries = ? WHERE file_path = ?",
                        (
                            json.dumps(updated_libraries),
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated > 0:
                        self.logger.debug(
                            f"Successfully updated 'uploaded_to_libraries' for {file_path} with libraries: {updated_libraries}"
                        )
                        conn.commit()
                    else:
                        self.logger.warning(
                            f"Failed to update 'uploaded_to_libraries' for file_path: {file_path}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update 'uploaded_to_libraries' for {file_path}: {e}"
                    )

    def update_uploaded_editions(self, file_path: str, new_editions: list):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "SELECT uploaded_editions FROM file_cache WHERE file_path = ?",
                        (file_path,),
                    )
                    result = cursor.fetchone()
                    if not result:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped"
                        )
                        return
                    current_editions = json.loads(result[0]) if result[0] else []
                    updated_editions = list(set(current_editions + new_editions))
                    cursor.execute(
                        "UPDATE file_cache SET uploaded_editions = ? WHERE file_path = ?",
                        (
                            json.dumps(updated_editions),
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated > 0:
                        self.logger.debug(
                            f"Successfully updated 'uploaded_editions' for {file_path} with libraries: {updated_editions}"
                        )
                        conn.commit()
                    else:
                        self.logger.warning(
                            f"Failed to update 'uploaded_editions' for file_path: {file_path}"
                        )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update 'uploaded_editions' for {file_path}: {e}"
                    )

    def update_webhook_flag(self, file_path: str, new_value=None):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET webhook_run = ? WHERE file_path = ?",
                        (
                            new_value,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'webhook_run' to {new_value} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to update 'webhook_run' for {file_path}: {e}"
                    )

    def clear_uploaded_to_libraries_and_editions(self, webhook_run: bool | None = None):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    if webhook_run is True:
                        cursor.execute(
                            "UPDATE file_cache SET uploaded_to_libraries = ?, uploaded_editions = ? WHERE webhook_run = ?",
                            ("[]", "[]", 1),
                        )
                    else:
                        cursor.execute(
                            "UPDATE file_cache SET uploaded_to_libraries = ?, uploaded_editions = ?",
                            ("[]", "[]"),
                        )
                    conn.commit()
                    self.logger.debug(
                        "Successfully reset uploaded_to_libraries and uploaded_editions to '[]'"
                    )
                except Exception as e:
                    conn.rollback()
                    self.logger.error(
                        f"Failed to clear uploaded_to_libraries and uploaded_editions data: {e}"
                    )

    def update_instance(self, file_path: str, instance: str):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET instance = ? WHERE file_path = ?",
                        (
                            instance,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'instance' to {instance} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'instance' for {file_path}: {e}"
                    )

    def update_arr_id(self, file_path: str, arr_id: int):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET arr_id = ? WHERE file_path = ?",
                        (
                            arr_id,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'arr_id' to {arr_id} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'arr_id' for {file_path}: {e}"
                    )

    def update_tmdb_id(self, file_path: str, tmdb_id: str):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET tmdb_id = ? WHERE file_path = ?",
                        (
                            tmdb_id,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'tmdb_id' to {tmdb_id} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'tmdb_id' for {file_path}: {e}"
                    )

    def update_imdb_id(self, file_path: str, imdb_id: str):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET imdb_id = ? WHERE file_path = ?",
                        (
                            imdb_id,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'imdb_id' to {imdb_id} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(
                        f"Failed to updated 'imdb_id' for {file_path}: {e}"
                    )

    def update_tvdb_id(self, file_path: str, tvdb_id: str):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET tvdb_id = ? WHERE file_path = ?",
                        (
                            tvdb_id,
                            file_path,
                        ),
                    )
                    rows_updated = cursor.rowcount
                    if rows_updated == 0:
                        self.logger.warning(
                            f"No matching row found for file_path: {file_path}. Update skipped."
                        )
                    else:
                        self.logger.debug(
                            f"Successfully updated 'tvdb_id' to {tvdb_id} for {file_path}"
                        )
                    conn.commit()
                except Exception as e:
                    self.logger.error(f"Failed to updated 'tvdb_id' for {tvdb_id}: {e}")

    def remove_upload_data_for_file(self, file_path: str) -> None:
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        "UPDATE file_cache SET uploaded_to_libraries = ?, uploaded_editions = ? WHERE file_path = ?",
                        ("[]", "[]", file_path),
                    )
                    conn.commit()
                    self.logger.info(
                        f"Successfully reset upload data for: '{file_path}'"
                    )
                except Exception as e:
                    conn.rollback()
                    self.logger.error(
                        f"Failed to clear uploaded_to_libraries and uploaded_editions data for {file_path}: {e}"
                    )

    def get_cached_file(self, file_path: str) -> dict[str, str] | None:
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT * FROM file_cache WHERE file_path = ?", (file_path,)
                )
                result = cursor.fetchone()
                if result:
                    return dict(result)
                else:
                    return None

    def delete_cached_file(self, file_path: str) -> None:
        with self.get_db_connection() as conn:
            try:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        "DELETE FROM file_cache WHERE file_path = ?", (file_path,)
                    )
                    conn.commit()
            except Exception as e:
                conn.rollback()
                self.logger.error(
                    f"Failed to remove item: '{file_path}' from database: {e}"
                )

    def return_all_files(self, webhook_run: bool | None = None) -> dict[str, dict]:
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                if webhook_run is True:
                    cursor.execute("SELECT * FROM file_cache WHERE webhook_run = 1")
                else:
                    cursor.execute("SELECT * FROM file_cache")

                result = cursor.fetchall()
                return {
                    file_path: {
                        "file_name": file_name,
                        "status": status,
                        "has_episodes": has_episodes,
                        "has_file": has_file,
                        "media_type": media_type,
                        "file_hash": file_hash,
                        "original_file_hash": original_file_hash,
                        "source_path": source_path,
                        "border_replaced": border_replaced,
                        "border_setting": border_setting,
                        "custom_color": custom_color,
                        "uploaded_to_libraries": self._safe_json_loads(
                            uploaded_to_libraries
                        ),
                        "uploaded_editions": self._safe_json_loads(uploaded_editions),
                        "webhook_run": webhook_flag,
                        "arr_id": arr_id,
                        "instance": instance,
                        "tmdb_id": tmdb_id,
                        "imdb_id": imdb_id,
                        "tvdb_id": tvdb_id,
                    }
                    for file_path, file_name, status, has_episodes, has_file, media_type, file_hash, original_file_hash, source_path, border_replaced, border_setting, custom_color, webhook_flag, uploaded_to_libraries, uploaded_editions, arr_id, instance, tmdb_id, imdb_id, tvdb_id in result
                }

    def _safe_json_loads(self, json_str: str | None) -> list:
        try:
            if not json_str or json_str.strip() == "":
                return []
            return json.loads(json_str)
        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON data encountered: {json_str}")
            return []

    def add_unmatched_movie(
        self,
        title: str,
        arr_id: int,
        instance: str,
        imdb_id: str,
        tmdb_id: str,
        is_missing: bool = False,
    ) -> None:
        try:
            with self.get_db_connection() as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        "SELECT id, arr_id, instance, imdb_id, tmdb_id, is_missing FROM unmatched_movies WHERE title = ?",
                        (title,),
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        cursor.execute(
                            """
                            INSERT INTO unmatched_movies (title, arr_id, instance, imdb_id, tmdb_id, is_missing)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                title,
                                arr_id,
                                instance,
                                imdb_id,
                                tmdb_id,
                                int(is_missing),
                            ),
                        )
                        self.logger.debug(
                            f"Added unmatched movie: title={title}, arr_id={arr_id}, instance={instance}, imdb_id={imdb_id}, tmdb_id={tmdb_id}, is_missing={is_missing}"
                        )
                    else:
                        (
                            movie_id,
                            existing_arr_id,
                            existing_instance,
                            existing_imdb_id,
                            existing_tmdb_id,
                            existing_is_missing,
                        ) = existing
                        if existing_arr_id is None or existing_arr_id != arr_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_movies
                                SET arr_id = ?
                                WHERE id = ?
                                """,
                                (arr_id, movie_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched movie: title={title}, arr_id={arr_id}"
                            )
                        if existing_instance is None or existing_instance != instance:
                            cursor.execute(
                                """
                                UPDATE unmatched_movies
                                SET instance = ?
                                WHERE id = ?
                                """,
                                (instance, movie_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched movie: title={title}, instance={instance}"
                            )
                        if existing_imdb_id is None or existing_imdb_id != imdb_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_movies
                                SET imdb_id = ?
                                WHERE id = ?
                                """,
                                (imdb_id, movie_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched movie: title={title}, imdb_id={imdb_id}"
                            )
                        if existing_tmdb_id is None or existing_tmdb_id != tmdb_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_movies
                                SET tmdb_id = ?
                                WHERE id = ?
                                """,
                                (tmdb_id, movie_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched movie: title={title}, tmdb_id={tmdb_id}"
                            )
                        if existing_is_missing != int(is_missing):
                            cursor.execute(
                                """
                                UPDATE unmatched_movies
                                SET is_missing = ?
                                WHERE id = ?
                                """,
                                (int(is_missing), movie_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched movie: title={title}, is_missing={is_missing}"
                            )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error adding unmatched movie: {e}")

    def add_unmatched_collection(
        self,
        title: str,
    ) -> None:
        try:
            with self.get_db_connection() as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        "SELECT id FROM unmatched_collections WHERE title = ?", (title,)
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        cursor.execute(
                            """
                            INSERT INTO unmatched_collections (title)
                            VALUES (?)
                            """,
                            (title,),
                        )
                        self.logger.debug(f"Added unmatched collection: title={title}")
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error adding unmatched collection: {e}")

    def add_unmatched_show(
        self,
        title: str,
        arr_id: int,
        main_poster_missing: bool,
        instance: str,
        imdb_id: str,
        tmdb_id: str,
        tvdb_id: str,
        is_missing: bool = False,
    ) -> int:
        try:
            with self.get_db_connection() as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        "SELECT id, arr_id, main_poster_missing, instance, imdb_id, tmdb_id, tvdb_id, is_missing FROM unmatched_shows WHERE title = ?",
                        (title,),
                    )
                    existing = cursor.fetchone()
                    show_id = None
                    if existing is None:
                        cursor.execute(
                            """
                            INSERT INTO unmatched_shows (title, arr_id, main_poster_missing, instance, imdb_id, tmdb_id, tvdb_id, is_missing)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                title,
                                arr_id,
                                int(main_poster_missing),
                                instance,
                                imdb_id,
                                tmdb_id,
                                tvdb_id,
                                int(is_missing),
                            ),
                        )
                        show_id = cursor.lastrowid
                        self.logger.debug(
                            f"Added unmatched show: title={title}, arr_id={arr_id}, main_poster_missing={bool(main_poster_missing)}, imdb_id={imdb_id}, tmdb_id={tmdb_id}, tvdb_id={tvdb_id}, is_missing={is_missing}"
                        )
                    else:
                        (
                            show_id,
                            current_arr_id,
                            current_main_poster_missing,
                            current_instance,
                            current_imdb_id,
                            current_tmdb_id,
                            current_tvdb_id,
                            current_is_missing,
                        ) = existing
                        if current_arr_id is None or current_arr_id != arr_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET arr_id = ?
                                WHERE id = ?
                                """,
                                (arr_id, show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched show: title={title} arr_id={arr_id}"
                            )
                        if current_main_poster_missing != int(main_poster_missing):
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET main_poster_missing = ?
                                WHERE id = ?
                                """,
                                (int(main_poster_missing), show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched show: title={title} main_poster_missing={bool(main_poster_missing)}"
                            )
                        if current_instance != instance:
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET instance = ?
                                WHERE id = ?
                                """,
                                (instance, show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched show: title={title}, instance={instance}"
                            )
                        if current_imdb_id is None or current_imdb_id != imdb_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET imdb_id = ?
                                WHERE id = ?
                                """,
                                (imdb_id, show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched show: title={title} imdb_id={imdb_id}"
                            )
                        if current_tmdb_id is None or current_tmdb_id != tmdb_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET tmdb_id = ?
                                WHERE id = ?
                                """,
                                (tmdb_id, show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched show: title={title} tmdb_id={tmdb_id}"
                            )
                        if current_tvdb_id is None or current_tvdb_id != tvdb_id:
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET tvdb_id = ?
                                WHERE id = ?
                                """,
                                (tvdb_id, show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched show: title={title} tvdb_id={tvdb_id}"
                            )
                        if current_is_missing != int(is_missing):
                            cursor.execute(
                                """
                                UPDATE unmatched_shows
                                SET is_missing = ?
                                WHERE id = ?
                                """,
                                (int(is_missing), show_id),
                            )
                            self.logger.debug(
                                f"Updated unmatched movie: title={title}, is_missing={is_missing}"
                            )
                conn.commit()
            if show_id is None:
                raise ValueError("Failed to insert unmatched show into the database.")

            return show_id
        except Exception as e:
            self.logger.error(f"Error adding unmatched show: {e}")
            raise

    def add_unmatched_season(
        self, show_id: int, season: str, is_missing: bool = False
    ) -> None:
        try:
            with self.get_db_connection() as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        "SELECT id, is_missing FROM unmatched_seasons WHERE show_id = ? AND season = ?",
                        (show_id, season),
                    )
                    existing = cursor.fetchone()
                    if existing is None:
                        cursor.execute(
                            """
                            INSERT INTO unmatched_seasons (show_id, season, is_missing)
                            VALUES (?, ?, ?)
                            """,
                            (show_id, season, int(is_missing)),
                        )
                    else:
                        season_id, existing_is_missing = existing
                        if existing_is_missing != int(is_missing):
                            cursor.execute(
                                "UPDATE unmatched_seasons SET is_missing = ? WHERE id = ?",
                                (int(is_missing), season_id),
                            )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error adding unmatched season: {e}")

    def get_unmatched_assets(self, db_table: str) -> list[dict[str, str]]:
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                if db_table == "unmatched_shows":
                    cursor.execute(
                        """
                        SELECT unmatched_shows.id, unmatched_shows.title, unmatched_shows.main_poster_missing, unmatched_shows.is_missing, unmatched_seasons.season, unmatched_seasons.is_missing AS season_is_missing
                        FROM unmatched_shows
                        LEFT JOIN unmatched_seasons ON unmatched_shows.id = unmatched_seasons.show_id
                        """
                    )
                    results = cursor.fetchall()
                    unmatched_shows = {}
                    for row in results:
                        show_id = row["id"]
                        if show_id not in unmatched_shows:
                            unmatched_shows[show_id] = {
                                "id": show_id,
                                "title": row["title"],
                                "main_poster_missing": bool(row["main_poster_missing"]),
                                "is_missing": bool(row["is_missing"]),
                                "seasons": [],
                            }
                        if row["season"]:
                            unmatched_shows[show_id]["seasons"].append(
                                {
                                    "season": row["season"],
                                    "is_missing": bool(row["season_is_missing"]),
                                }
                            )
                    return list(unmatched_shows.values())
                else:
                    cursor.execute(f"SELECT * FROM {db_table}")
                    results = cursor.fetchall()
                return [dict(result) for result in results]

    def get_unmatched_arr_ids(self, db_table: str) -> list[tuple[int, str]]:
        unmatched_data = []
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(
                        f"""
                        SELECT arr_id, instance FROM {db_table}
                        """
                    )
                    results = cursor.fetchall()
                    unmatched_data = [(int(row[0]), row[1]) for row in results]
                except Exception as e:
                    self.logger.error(
                        f"Failed to fetch unmatched arr_ids from {db_table}: {e}"
                    )
        return unmatched_data

    def get_all_unmatched_assets(self):
        unmatched_media = {
            "movies": self.get_unmatched_assets("unmatched_movies"),
            "shows": self.get_unmatched_assets("unmatched_shows"),
            "collections": self.get_unmatched_assets("unmatched_collections"),
        }
        return unmatched_media

    def delete_unmatched_asset(self, db_table, title):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(f"DELETE FROM {db_table} WHERE title = ?", (title,))
            conn.commit()

    def delete_unmatched_season(self, show_id: int, season: str):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                    DELETE FROM unmatched_seasons
                    WHERE show_id = ? AND season = ?
                    """,
                    (show_id, season),
                )
                conn.commit()

    def wipe_unmatched_assets(self):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("DELETE FROM unmatched_movies")
                cursor.execute("DELETE FROM unmatched_collections")
                cursor.execute("DELETE FROM unmatched_shows")
                cursor.execute("DELETE FROM unmatched_seasons")
                conn.commit()

    def initialize_stats(self) -> None:
        try:
            with self.get_db_connection() as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        """
                        INSERT INTO unmatched_stats (id, total_collections, total_movies_all, total_series_all, total_seasons_all, total_movies_with_file, total_series_with_episodes, total_seasons_with_episodes)
                        VALUES (1, 0, 0, 0, 0, 0, 0, 0)
                        ON CONFLICT(id) DO NOTHING
                        """
                    )
                    self.logger.debug(
                        f"initialize_stats: row exists or was created, rows affected: {cursor.rowcount}"
                    )
        except Exception as e:
            self.logger.error(f"Initialize_stats failed: {e}", exc_info=True)

    def update_stats(self, stats: dict[str, int]) -> None:
        try:
            with self.get_db_connection() as conn:
                with closing(conn.cursor()) as cursor:
                    columns = ", ".join(f"{key} = ?" for key in stats.keys())
                    values = tuple(stats.values())
                    full_values = values + values
                    self.logger.debug(f"update_stats writing: {stats}")

                    cursor.execute(
                        f"""
                        INSERT INTO unmatched_stats (id, {", ".join(stats.keys())})
                        VALUES (1, {", ".join("?" for _ in stats.keys())})
                        ON CONFLICT(id)
                        DO UPDATE SET {columns}
                        """,
                        full_values,
                    )
                    conn.commit()
                    self.logger.debug(
                        f"update_stats committed successfully, rows affected {cursor.rowcount}"
                    )
        except Exception as e:
            self.logger.error(f"update_stats failed: {e}", exc_info=True)

    def cleanup_orhpaned_seasons(self):
        with self.get_db_connection() as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """
                    DELETE FROM unmatched_seasons
                    WHERE show_id NOT IN (SELECT id FROM unmatched_shows)
                    """
                )
                deleted = cursor.rowcount
                if deleted:
                    self.logger.info(
                        f"Cleaned up {deleted} orphaned season(s) from unmatched_seasons"
                    )
            conn.commit()
