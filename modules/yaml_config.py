import json
import logging
from logging import Logger
from pathlib import Path

import yaml

from modules.settings import Settings
from Payloads.plex_uploader_payload import Payload as PlexUploaderrPayload
from Payloads.poster_renamerr_payload import Payload as PosterRenamerPayload
from Payloads.unmatched_assets_payload import Payload as UnmatchedAssetsPayload

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


class YamlConfig:
    def __init__(
        self,
        logger: Logger,
        config_path=Settings.CONFIG_PATH.value,
    ):
        self.logger = logger
        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, "r") as file:
                config = yaml.safe_load(file)
        except FileNotFoundError as e:
            self.logger.error(f"Config file not found at {self.config_path}: {e}")
            raise e
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing config file {self.config_path}: {e}")
            raise e

        self.schedule_config = config["schedule"]
        self.log_level_config = config["log_level"]

        instances_config = config["instances"]
        self.radarr_config = instances_config.get("radarr", {})
        self.sonarr_config = instances_config.get("sonarr", {})
        self.plex_config = instances_config.get("plex", {})
        return config

    def create_poster_renamer_payload(self) -> PosterRenamerPayload:
        plex_uploader_config = self.config.get(Settings.PLEX_UPLOADERR.value)
        script_config = self.config.get(Settings.POSTER_RENAMERR.value)
        log_level_str = self.log_level_config.get("poster_renamerr", "INFO").upper()
        log_level = LOG_LEVELS.get(log_level_str, logging.INFO)
        border_setting = script_config.get("border_setting", None)
        if border_setting == "black":
            custom_color = "#000000"
        else:
            custom_color = script_config.get("hex_code", "")

        payload_data = {
            "log_level": log_level,
            "source_dirs": script_config.get("source_directories", []),
            "target_path": script_config.get("target_directory", ""),
            "asset_folders": script_config.get("asset_folders", False),
            "clean_assets": script_config.get("clean_assets", False),
            "unmatched_assets": script_config.get("unmatched_assets", True),
            "replace_border": script_config.get("replace_border", False),
            "border_setting": border_setting,
            "custom_color": custom_color,
            "upload_to_plex": script_config.get("upload_to_plex", False),
            "match_alt": script_config.get("match_alt", False),
            "only_unmatched": script_config.get("only_unmatched", False),
            "reapply_posters": plex_uploader_config.get("reapply_posters", False),
            "library_names": script_config.get("library_names", []),
            "instances": script_config.get("instances", []),
            "radarr": self.radarr_config,
            "sonarr": self.sonarr_config,
            "plex": self.plex_config,
        }
        self.logger.debug("===" * 10 + " PosterRenamerr Payload " + "===" * 10)
        self.logger.debug(json.dumps(payload_data, indent=4))
        return PosterRenamerPayload(**payload_data)

    def create_unmatched_assets_payload(self) -> UnmatchedAssetsPayload:
        renamer_config = self.config.get(Settings.POSTER_RENAMERR.value)
        script_config = self.config.get(Settings.UNMATCHED_ASSETS.value)
        log_level_str = self.log_level_config.get("unmatched_assets", "INFO").upper()
        log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

        payload_data = {
            "log_level": log_level,
            "target_path": renamer_config.get("target_directory", ""),
            "asset_folders": renamer_config.get("asset_folders", False),
            "show_all_unmatched": script_config.get("show_all_unmatched", False),
            "library_names": renamer_config.get("library_names", []),
            "instances": renamer_config.get("instances", []),
            "radarr": self.radarr_config,
            "sonarr": self.sonarr_config,
            "plex": self.plex_config,
        }
        self.logger.debug("===" * 10 + " UnmatchedAssets Payload " + "===" * 10)
        self.logger.debug(json.dumps(payload_data, indent=4))
        return UnmatchedAssetsPayload(**payload_data)

    def create_plex_uploaderr_payload(self) -> PlexUploaderrPayload:
        renamer_config = self.config.get(Settings.POSTER_RENAMERR.value)
        script_config = self.config.get(Settings.PLEX_UPLOADERR.value)
        log_level_str = self.log_level_config.get("plex_uploaderr", "INFO").upper()
        log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

        payload_data = {
            "log_level": log_level,
            "asset_folders": renamer_config.get("asset_folders", False),
            "reapply_posters": script_config.get("reapply_posters", False),
            "library_names": renamer_config.get("library_names", []),
            "instances": renamer_config.get("instances", []),
            "plex": self.plex_config,
            "radarr": self.radarr_config,
            "sonarr": self.sonarr_config,
        }
        self.logger.debug("===" * 10 + " PlexUploaderr Payload " + "===" * 10)
        self.logger.debug(json.dumps(payload_data, indent=4))
        return PlexUploaderrPayload(**payload_data)

    def get_run_single_item(self) -> bool:
        return self.config.get(Settings.POSTER_RENAMERR.value).get(
            "run_single_item", False
        )
