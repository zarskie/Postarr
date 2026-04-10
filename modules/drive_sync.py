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
    RCLONE_IMPORTANT = (
        "Transferred:",
        "Transferring:",
        " * ",
        "Errors:",
        "Checks:",
        "Elapsed time:",
        "ERROR",
        "NOTICE",
    )

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
            self.logger.exception("Failed to initialize DriveSync")
            raise e

    def remote_exists(self, remote_name: str) -> bool:
        try:
            result = subprocess.run(
                ["rclone", "listremotes"], capture_output=True, text=True, check=True
            )
            exists = f"{remote_name}:" in result.stdout
            if exists:
                self.logger.debug(
                    f"Remote '{remote_name}' already exists. Skipping creation."
                )

            return exists
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error checking remotes: {e.stderr}")
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
            self.logger.info(f"Remote '{remote_name}' created successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create remote '{remote_name}': {e.stderr}")

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
                    if any(key in line for key in self.RCLONE_IMPORTANT):
                        self.logger.info(f"[{drive_name}] {line}")
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
                self.logger.error(f"Problem rotating rclone log file: {e}")

        for drive in self.gdrives:
            drive_name = drive["drive_name"]
            drive_location = drive["drive_location"]
            drive_id = drive["drive_id"]

            if (
                self.client_id and self.client_secret and self.oauth_token
            ) and not self.service_account:
                self.logger.debug(f"Attempting OAuth authentication for '{drive_name}'")
            elif self.service_account:
                self.logger.debug(
                    f"Attempting Service Account authentication for '{drive_name}'"
                )
            else:
                self.logger.warning(
                    f"No authentication provided for '{drive_name}'. Skipping"
                )
                current_progress += progress_step
                if cb and job_id:
                    cb(
                        job_id,
                        min(current_progress, 99),
                        ProgressState.IN_PROGRESS,
                    )
                continue

            self.logger.info(f"Starting sync for: '{drive_name}' ⟶ '{drive_location}'")
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
                self.logger.trace(  # type: ignore[attr-defined]
                    f"Trace logging enabled, rclone log at: {rclone_log_path}"
                )
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
            self.logger.debug(
                f"Rclone command:\n{' '.join(sanitize_command_for_log(rclone_command))}"
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
                    self.logger.info(f"Sync completed for drive: {drive_name}")
                    current_progress += progress_step
                    if cb and job_id:
                        cb(
                            job_id,
                            min(current_progress, 99),
                            ProgressState.IN_PROGRESS,
                        )
                else:
                    self.logger.error(
                        f"Sync failed for drive name: '{drive_name}' with return code {process.returncode}"
                    )
                    current_progress += progress_step
                    if cb and job_id:
                        cb(
                            job_id,
                            min(current_progress, 99),
                            ProgressState.IN_PROGRESS,
                        )

            except Exception as e:
                self.logger.error(f"Sync failed for drive '{drive_name}': {e}")
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
            f"Finished syncing {total_drives} drive(s), full rclone log available at: {rclone_log_path}"
        )
        if cb and job_id:
            cb(job_id, 99, ProgressState.IN_PROGRESS)
