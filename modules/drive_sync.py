import json
import logging
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from modules import Settings
from modules.logger import init_logger
from progress import ProgressState


class DriveSync:
    def __init__(self, payload):
        self.logger = logging.getLogger("DriveSync")
        try:
            self.log_dir = Path(Settings.LOG_DIR.value) / Settings.DRIVE_SYNC.value
            init_logger(
                self.logger,
                self.log_dir,
                "drive_sync",
                log_level=payload.log_level if payload.log_level else logging.INFO,
            )
            self.client_id = payload.client_id
            self.rclone_token = payload.rclone_token
            self.rclone_secret = payload.rclone_secret
            self.service_account = payload.service_account
            self.gdrives = payload.gdrives
        except Exception as e:
            self.logger.exception("Failed to initialize DriveSync")
            raise e

    def _log_banner(self, job_id):
        self.logger.info("\n" + "#" * 80)
        self.logger.info(f"### New DriveSync Run -- Job ID: '{job_id}'")
        self.logger.info("\n" + "#" * 80)

    def remote_exists(self, remote_name: str) -> bool:
        try:
            result = subprocess.run(
                ["rclone", "listremotes"], capture_output=True, text=True, check=True
            )
            exists = f"{remote_name}:" in result.stdout
            if exists:
                self.logger.info(
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

    def sync_all_drives(
        self,
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
    ):
        self._log_banner(job_id)
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

        # rotate the prior log file and also delete older log files
        # could consider setting up something more official w/ logrotate perhaps?
        # but this should suffice.
        rclone_log_dir = "/config/"
        rclone_log_file = "rclone.log"
        rclone_rotated_log_suffix = "1"
        rclone_full_log_path = rclone_log_dir + rclone_log_file
        rclone_rotated_log_path = rclone_full_log_path + rclone_rotated_log_suffix
        if os.path.isfile(rclone_full_log_path):
            try:
                if os.path.isfile(rclone_rotated_log_path):
                    os.remove(rclone_rotated_log_path)
                os.rename(rclone_full_log_path, rclone_rotated_log_path)
            except Exception as e:
                self.logger.error(f"Problem rotating rclone log file: {e}")
                self.logger.error(f"rclone log file full path: {rclone_full_log_path}")
                self.logger.error(
                    f"rclone log file rotated path: {rclone_full_log_path + rclone_rotated_log_suffix}"
                )

        for drive in self.gdrives:
            drive_name = drive["drive_name"]
            drive_location = drive["drive_location"]
            drive_id = drive["drive_id"]

            if (
                self.client_id and self.rclone_secret and self.rclone_token
            ) and not self.service_account:
                self.logger.debug(f"Using OAuth authentication for '{drive_name}'")
            elif self.service_account:
                self.logger.debug(
                    f"Using Service Account authentication for '{drive_name}'"
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

            self.logger.info(f"Starting sync for: '{drive_name}' -> '{drive_location}'")
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
                # "--check-first",
                "--bwlimit=80M",
                "--size-only",
                "--delete-during",
                "-v",
            ]

            if self.logger.isEnabledFor(logging.DEBUG):
                rclone_command.append(f"--log-file={rclone_full_log_path}")

            # Initialize using OAuth
            if self.client_id and self.rclone_secret and self.rclone_token:
                rclone_command.extend(["--drive-client-id", self.client_id])
                rclone_command.extend(["--drive-client-secret", self.rclone_secret])
                rclone_command.extend(["--drive-token", self.rclone_token])

            # Initialize using service account
            if self.service_account:
                rclone_command.extend(
                    ["--drive-service-account-file", self.service_account]
                )

            self.logger.debug("Rclone command:")
            self.logger.debug(json.dumps(rclone_command, indent=4))

            try:
                process = subprocess.Popen(
                    rclone_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1,
                    universal_newlines=True,
                )
                if process.stdout is not None:
                    for line in iter(process.stdout.readline, ""):
                        self.logger.info(f"[{drive_name}] {line.strip()}")

                if process.stderr is not None:
                    for line in iter(process.stderr.readline, ""):
                        self.logger.info(f"[{drive_name}] {line.strip()}")

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
                        f"Sync failed for Drive ID: '{drive_id}' with errors"
                    )
                    current_progress += progress_step
                    if cb and job_id:
                        cb(
                            job_id,
                            min(current_progress, 99),
                            ProgressState.IN_PROGRESS,
                        )

            except subprocess.CalledProcessError as e:
                self.logger.error(f"Sync failed for Drive ID '{drive_id}': {e.stderr}")
                current_progress += progress_step
                if cb and job_id:
                    cb(
                        job_id,
                        min(current_progress, 99),
                        ProgressState.IN_PROGRESS,
                    )

        self.logger.info("Finished sync of all drives.")
        if cb and job_id:
            cb(job_id, 99, ProgressState.IN_PROGRESS)
