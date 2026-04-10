import json
import logging
import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from modules.logger import init_logger
from modules.settings import Settings
from modules.utils import log_banner
from postarr.utils.webui_utils import sanitize_command_for_log
from progress import ProgressState


class DriveSync:
    RCLONE_INFO = (
        "Transferred:",
        "Transferring:",
        " * ",
        "Errors:",
        "Checks:",
        "Elapsed time:",
        "NOTICE",
    )
    RCLONE_ERROR = ("ERROR",)

    def __init__(self, payload):
        self.logger = logging.getLogger(Settings.DRIVE_SYNC.value)
        try:
            self.log_dir = Path(Settings.LOG_DIR.value) / Settings.DRIVE_SYNC.value
            init_logger(
                self.logger,
                self.log_dir,
                "drive_sync",
                log_level=payload.log_level if payload.log_level else logging.INFO,
            )
            self.client_id = payload.client_id
            self.oauth_token = payload.oauth_token
            self.client_secret = payload.client_secret
            self.service_account = payload.service_account
            self.gdrives = payload.gdrives
        except Exception as e:
            self.logger.error("Failed to initialize drive sync %s", e, exc_info=True)
            raise

    def remote_exists(self, remote_name: str) -> bool:
        try:
            result = subprocess.run(
                ["rclone", "listremotes"], capture_output=True, text=True, check=True
            )
            exists = f"{remote_name}:" in result.stdout
            if exists:
                self.logger.trace(  # type: ignore[attr-defined]
                    "Remote '%s' already exists, skipping creation", remote_name
                )

            return exists
        except subprocess.CalledProcessError as e:
            self.logger.error("Error checking remotes: %s", e.stderr)
            return False

    def create_remote(self):
        remote_name = "posters"
        if self.remote_exists(remote_name):
            return
        try:
            subprocess.run(
                [
                    "rclone",
                    "config",
                    "create",
                    remote_name,
                    "drive",
                    "config_is_local=false",
                ],
                check=True,
            )
            self.logger.info("Remote '%s' created successfully", remote_name)
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to create remote '%s': %s", remote_name, e.stderr)

    def tail_log(self, log_path, drive_name, stop_event):
        while not stop_event.is_set() and not os.path.exists(log_path):
            stop_event.wait(0.5)
        if not os.path.exists(log_path):
            return
        with open(log_path, "r") as f:
            f.seek(0, 2)
            while not stop_event.is_set():
                line = f.readline()
                if line:
                    line = line.strip()
                    if any(key in line for key in self.RCLONE_ERROR):
                        self.logger.error("[%s] %s", drive_name, line)
                    elif any(key in line for key in self.RCLONE_INFO):
                        self.logger.info("[%s] %s", drive_name, line)
                else:
                    stop_event.wait(0.5)

    def sync_all_drives(
        self,
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
    ):
        log_banner(self.logger, Settings.DRIVE_SYNC.value, job_id)
        self.create_remote()
        total_drives = len(self.gdrives)

        if total_drives == 0:
            self.logger.warning("No drives found for syncing.")
            if cb and job_id:
                cb(job_id, 100, ProgressState.COMPLETED)
            return

        current_progress = 10
        if cb and job_id:
            cb(job_id, current_progress, ProgressState.IN_PROGRESS)

        progress_step = 90 // total_drives if total_drives > 0 else 90

        rclone_log_dir = Path(Settings.LOG_DIR.value) / "rclone"
        rclone_log_dir.mkdir(parents=True, exist_ok=True)
        rclone_log_path = rclone_log_dir / "rclone.log"
        rclone_rotated_log_path = rclone_log_dir / "rclone.log.1"
        if os.path.isfile(rclone_log_path):
            try:
                if os.path.isfile(rclone_rotated_log_path):
                    os.remove(rclone_rotated_log_path)
                os.rename(rclone_log_path, rclone_rotated_log_path)
            except Exception as e:
                self.logger.error(
                    "Problem rotating rclone log file: %s", e, exc_info=True
                )

        self.logger.trace(  # type: ignore[attr-defined]
            "Trace logging enabled, rclone log at: %s", rclone_log_path
        )
        self.logger.trace("Gdrive dump:%s\n", json.dumps(self.gdrives, indent=2))  # type: ignore[attr-defined]

        for drive in self.gdrives:
            drive_name = drive["drive_name"]
            drive_location = drive["drive_location"]
            drive_id = drive["drive_id"]

            if (
                self.client_id and self.client_secret and self.oauth_token
            ) and not self.service_account:
                self.logger.debug(
                    "Attempting OAuth authentication for '%s'", drive_name
                )

            elif self.service_account:
                self.logger.debug(
                    "Attempting Service Account authentication for '%s'", drive_name
                )
            else:
                self.logger.warning(
                    "No authentication provided for '%s', skipping", drive_name
                )
                current_progress += progress_step
                if cb and job_id:
                    cb(
                        job_id,
                        min(current_progress, 99),
                        ProgressState.IN_PROGRESS,
                    )
                continue

            self.logger.info(
                "Starting sync for: '%s' ⟶ '%s'", drive_name, drive_location
            )
            rclone_command = [
                "rclone",
                "sync",
                "posters:",
                drive_location,
                "--drive-root-folder-id",
                drive_id,
                "--fast-list",
                "--tpslimit=5",
                "--no-update-modtime",
                "--drive-use-trash=false",
                "--drive-chunk-size=512M",
                "--exclude=**.partial",
                "--bwlimit=80M",
                "--size-only",
                "--delete-during",
                f"--log-file={rclone_log_path}",
            ]

            if self.logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
                rclone_command.append("-vvv")
            elif self.logger.isEnabledFor(logging.DEBUG):
                rclone_command.append("-vv")
            else:
                rclone_command.append("-v")

            # Initialize using OAuth
            if self.client_id and self.client_secret and self.oauth_token:
                rclone_command.extend(
                    [
                        "--drive-client-id",
                        self.client_id,
                        "--drive-client-secret",
                        self.client_secret,
                        "--drive-token",
                        self.oauth_token,
                    ]
                )

            # Initialize using service account
            if self.service_account:
                rclone_command.extend(
                    ["--drive-service-account-file", self.service_account]
                )
            self.logger.trace(  # type: ignore[attr-defined]
                "Rclone command: '%s'",
                " ".join(sanitize_command_for_log(rclone_command)),
            )
            stop_event = threading.Event()
            tail_thread = threading.Thread(
                target=self.tail_log,
                args=(rclone_log_path, drive_name, stop_event),
                daemon=True,
            )
            tail_thread.start()
            try:
                process = subprocess.Popen(
                    rclone_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1,
                    universal_newlines=True,
                )

                process.wait()

                if process.returncode == 0:
                    self.logger.info("Sync completed for drive: '%s'", drive_name)
                    current_progress += progress_step
                    if cb and job_id:
                        cb(
                            job_id,
                            min(current_progress, 99),
                            ProgressState.IN_PROGRESS,
                        )
                else:
                    self.logger.error(
                        "Sync failed for drive name: '%s' with return code %s",
                        drive_name,
                        process.returncode,
                    )
                    current_progress += progress_step
                    if cb and job_id:
                        cb(
                            job_id,
                            min(current_progress, 99),
                            ProgressState.IN_PROGRESS,
                        )

            except Exception as e:
                self.logger.error(
                    "Sync failed for drive '%s': %s", drive_name, e, exc_info=True
                )
                current_progress += progress_step
                if cb and job_id:
                    cb(
                        job_id,
                        min(current_progress, 99),
                        ProgressState.IN_PROGRESS,
                    )
            finally:
                stop_event.set()
                tail_thread.join()

        self.logger.info(
            "Finished syncing %s drive(s), full rclone log available at: %s",
            total_drives,
            rclone_log_path,
        )
        if cb and job_id:
            cb(job_id, 99, ProgressState.IN_PROGRESS)
