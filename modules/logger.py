import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def init_logger(
    lgr: logging.Logger, log_dir: Path, file_name: str, log_level: int = 20
):
    """
    Levels: (lvl)
    CRITICAL 50
    ERROR 40
    WARNING 30
    INFO 20
    DEBUG 10
    NOTSET 0
    """
    # ensure all parents exist
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(
            f"PermissionError: {e} - Check Docker volume permissions for {log_dir}",
            flush=True,
        )
    except Exception as e:
        print(f"Failed to create directory: {e}", flush=True)

    lgr.handlers.clear()

    # set log level
    lgr.setLevel(log_level)

    # format the logger
    formatter = logging.Formatter(
        "[%(name)s][%(threadName)s][%(asctime)s][%(levelname)s] = %(message)s"
    )

    if log_level == logging.DEBUG:
        file_name = f"{file_name}_debug.log"
    else:
        file_name = f"{file_name}.log"

    file_path = log_dir / file_name

    max_bytes_multiplier = float(os.environ.get("LOGGER_MAX_BYTES_MULTIPLIER", 1))
    if max_bytes_multiplier and isinstance(max_bytes_multiplier, (int, float, complex)):
        if max_bytes_multiplier <= 0:
            max_bytes_multiplier = 1
    else:
        max_bytes_multiplier = 1

    max_backup_files = int(os.environ.get("LOGGER_MAX_BACKUP_FILES", 10))
    if max_backup_files and isinstance(max_backup_files, (int, float, complex)):
        if max_backup_files < 10:
            max_backup_files = 10  # minimum of 10
    else:
        max_backup_files = 10

    # Configure RotatingFileHandler for the logger
    file_handler = RotatingFileHandler(
        file_path,
        mode="a",
        maxBytes=10 * 1024 * 1024 * max_bytes_multiplier,
        backupCount=max_backup_files,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    lgr.addHandler(file_handler)

    # Configure a stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    lgr.addHandler(stream_handler)

    return lgr
