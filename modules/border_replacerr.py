import logging
import shutil
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from modules.database_cache import Database
from modules.logger import init_logger
from modules.settings import Settings
from modules.utils import hash_file, log_banner
from progress import ProgressState


class BorderReplacerr:
    def __init__(self, custom_color=None, payload=None) -> None:
        if payload:
            self.logger = logging.getLogger(Settings.BORDER_REPLACERR.value)
            try:
                log_dir = Path(Settings.LOG_DIR.value) / Settings.BORDER_REPLACERR.value
                init_logger(
                    self.logger,
                    log_dir,
                    "border_replacerr",
                    log_level=payload.log_level if payload.log_level else logging.INFO,
                )
                self.db = Database(self.logger)
                self.target_path = Path(payload.target_path)
                self.backup_path = Path(Settings.ORIGINAL_POSTERS.value)
                self.border_setting = payload.border_setting
                self.custom_color = payload.custom_color
                self.asset_folders = payload.asset_folders

            except Exception as e:
                self.logger.error(
                    "Failed to initialize border replacerr: %s", e, exc_info=True
                )
                raise
        else:
            # used by PosterRenamerr for image processing only — logger not available
            self.custom_color = custom_color

    def remove_border(self, image_path: Path):
        image = Image.open(image_path)
        width, height = image.size
        crop_area = (26, 26, width - 26, height)

        final_image = image.crop(crop_area)
        bottom_border = Image.new("RGB", (width - 2 * 26, 26), color="black")  # type: ignore[arg-type]
        bottom_border_position = (0, final_image.size[1] - 26)
        final_image.paste(bottom_border, bottom_border_position)
        final_image = final_image.resize((1000, 1500)).convert("RGB")

        return final_image

    def replace_border(self, image_path: Path):
        if not self.custom_color:
            self.logger.error("custom_color is not set, cannot replace border")
            return Image.open(image_path)
        image = Image.open(image_path)
        width, height = image.size
        crop_area = (26, 26, width - 26, height - 26)
        cropped_image = image.crop(crop_area)
        new_image = Image.new("RGB", (width, height), color=self.custom_color)
        new_image.paste(cropped_image, (26, 26))
        final_image = new_image.resize((1000, 1500)).convert("RGB")
        return final_image

    def replace_current_assets(
        self,
        cb: Callable[[str, int, ProgressState], None] | None = None,
        job_id: str | None = None,
    ):
        try:
            log_banner(self.logger, Settings.BORDER_REPLACERR.value, job_id)
            original_poster_paths = [
                poster for poster in self.backup_path.rglob("*") if poster.is_file()
            ]
            total = len(original_poster_paths)
            if job_id and cb:
                cb(job_id, 20, ProgressState.IN_PROGRESS)
            for i, poster in enumerate(original_poster_paths):
                try:
                    relative_path = poster.relative_to(self.backup_path)
                    target_path = self.target_path / relative_path

                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    if self.border_setting is None:
                        shutil.copy2(poster, target_path)
                        self.logger.trace("Restored original poster: %s", target_path)  # type: ignore[attr-defined]
                        file_hash = hash_file(target_path, self.logger)
                        self.db.update_border_replaced_hash(
                            str(target_path),
                            file_hash,
                            False,
                            self.border_setting,
                            self.custom_color,
                        )
                        if job_id and cb and total > 0:
                            progress = 20 + int(((i + 1) / total) * 80)
                            cb(job_id, progress, ProgressState.IN_PROGRESS)
                        continue
                    elif self.border_setting == "remove":
                        new_image = self.remove_border(poster)
                        self.logger.trace("Removed border for: %s", poster)  # type: ignore[attr-defined]
                    elif self.border_setting in ["custom", "black"]:
                        new_image = self.replace_border(poster)
                        self.logger.trace("Replaced border for: %s", poster)  # type: ignore[attr-defined]
                    else:
                        self.logger.warning(
                            "Unsupported border setting '%s' for: %s",
                            self.border_setting,
                            poster,
                        )
                        continue

                    new_image.save(target_path)
                    self.logger.trace("Updated asset saved: %s", target_path)  # type: ignore[attr-defined]

                    file_hash = hash_file(target_path, self.logger)
                    self.db.update_border_replaced_hash(
                        str(target_path),
                        file_hash,
                        True,
                        self.border_setting,
                        self.custom_color,
                    )
                    if job_id and cb and total > 0:
                        progress = 20 + int(((i + 1) / total) * 80)
                        cb(job_id, progress, ProgressState.IN_PROGRESS)
                except Exception as e:
                    self.logger.error("Error processing file '%s': %s", poster, e)
            self.logger.info("Border replacerr complete — %s asset(s) processed", total)
            if job_id and cb:
                cb(job_id, 100, ProgressState.COMPLETED)
        except Exception as e:
            self.logger.error(
                "Critical error during asset replacement: %s", e, exc_info=True
            )
