import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from postarr.config.config import Config


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

    # Configure RotatingFileHandler for the logger
    file_handler = RotatingFileHandler(
        file_path, mode="a", maxBytes=10 * 1024 * 1024, backupCount=10
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


def get_postarr_logger():
    global_config = Config()
    logger = logging.getLogger("postarr-web")
    ap_scheduler_logger = logging.getLogger("apscheduler")
    if not logger.hasHandlers():
        log_level_str = getattr(global_config, "MAIN_LOG_LEVEL", "INFO")
        log_level = getattr(logging, log_level_str, logging.INFO)
        init_logger(logger, global_config.logs / "web-ui", "web_ui", log_level)
        init_logger(
            ap_scheduler_logger,
            global_config.logs / "web-ui",
            "ap_scheduler",
            log_level,
        )
    return logger
