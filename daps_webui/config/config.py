import os
from pathlib import Path


class Config:
    _base = Path(os.environ.get("APP_DATA_DIR", "/config"))
    logs = _base / "logs"
    database = _base / "db"
    # log level
    MAIN_LOG_LEVEL = os.environ.get("MAIN_LOG_LEVEL", "INFO").upper()
    # environment
    FLASK_ENV = os.environ.get("FLASK_ENV")
    # version
    VERSION = os.environ.get("VERSION")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(database / 'database.db')}"

    @classmethod
    def init_directories(cls):
        cls.logs.mkdir(exist_ok=True, parents=True)
        cls.database.mkdir(exist_ok=True, parents=True)
