import os
import re
from collections import defaultdict
from pathlib import Path
from pprint import pformat

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

import modules.settings
from postarr import (
    db,
    models,
    postarr_logger,
    run_border_replacer_task,
    run_drive_sync_task,
    run_plex_uploaderr_task,
    run_renamer_task,
    run_unmatched_assets_task,
)
from postarr.models import CurrentJobs, JobHistory
from postarr.utils.database import Database
from postarr.utils.webhook_manager import WebhookManager
from progress import progress_instance

poster_renamer = Blueprint("poster_renamer", __name__)
database = Database(db, postarr_logger)


@poster_renamer.route("/poster-renamer")
def poster_renamer_route():
    return render_template("poster_renamer/poster_renamer.html")


@poster_renamer.route("/serve-image/<path:filename>", methods=["GET"])
def serve_image(filename):
    settings = models.Settings.query.first()
    asset_folders = getattr(settings, "asset_folders", False)
    assets_directory = getattr(settings, "target_path", "")
    if not assets_directory:
        return (
            jsonify({"success": False, "message": "No target path found in settings."}),
            500,
        )
    try:
        if asset_folders:
            parent_dir, name = filename.split("/", 1)
            file_path = f"{parent_dir}/{name}"
        else:
            file_path = filename

        return send_from_directory(assets_directory, file_path)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@poster_renamer.route("/get-file-paths", methods=["GET"])
def get_images():
    try:
        settings = models.Settings.query.first()
        asset_folders = getattr(settings, "asset_folders", False)
        assets_directory = getattr(settings, "target_path", "")
        if not assets_directory:
            return (
                jsonify(
                    {"success": False, "message": "No target path found in settings."}
                ),
                500,
            )

        file_cache_entries = models.FileCache.query.all()
        sorted_files = {"movies": [], "shows": {}, "collections": []}

        if asset_folders:
            season_pattern = re.compile(r"^Season(?P<season>\d{2})\.(?P<ext>\w+)$")
            show_movie_pattern = re.compile(r"^poster\.(?P<ext>\w+)$")
        else:
            season_pattern = re.compile(
                r"^(?P<name>.+ \(\d{4}\)(?: \{.+\})?)_Season(?P<season>\d{2})\.(?P<ext>\w+)$"
            )
            show_movie_pattern = re.compile(
                r"^(?P<name>.+ \(\d{4}\)(?: \{.+\})?)\.(?P<ext>\w+)$"
            )

        def strip_id(name: str) -> str:
            return re.sub(r"\{.*?\}", "", name)

        shows_dict = {}

        for file in file_cache_entries:
            file_name = Path(file.file_path).name
            parent_dir = Path(file.file_path).parent.name
            file_name_without_suffix = Path(file.file_path).stem

            file_name_stripped = strip_id(file_name_without_suffix)
            parent_dir_stripped = strip_id(parent_dir)
            if asset_folders:
                if not season_pattern.match(file_name) and not show_movie_pattern.match(
                    file_name
                ):
                    continue
            else:
                folder_season_pattern = re.compile(
                    r"^Season(?P<season>\d{2})\.(?P<ext>\w+)$"
                )
                folder_show_movie_pattern = re.compile(r"^poster\.(?P<ext>\w+)$")

                if folder_season_pattern.match(
                    file_name
                ) or folder_show_movie_pattern.match(file_name):
                    continue

            file_data = {
                "file_name": (
                    parent_dir_stripped if asset_folders else file_name_stripped
                ),
                "file_path": (
                    f"/serve-image/{parent_dir}/{file_name}"
                    if asset_folders
                    else f"/serve-image/{file_name}"
                ),
                "source_path": file.source_path,
                "file_hash": file.file_hash,
            }
            if file.media_type == "movies":
                sorted_files["movies"].append(file_data)
            elif file.media_type == "collections":
                sorted_files["collections"].append(file_data)
            else:
                show_match = show_movie_pattern.match(file_name)
                season_match = season_pattern.match(file_name)
                if show_match:
                    show_name = (
                        parent_dir_stripped
                        if asset_folders
                        else strip_id(show_match.group("name"))
                    )
                    if show_name not in shows_dict:
                        shows_dict[show_name] = {
                            "file_name": show_name,
                            "file_path": (
                                f"/serve-image/{parent_dir}/{file_name}"
                                if asset_folders
                                else f"/serve-image/{file_name}"
                            ),
                            "source_path": file.source_path,
                            "file_hash": file.file_hash,
                            "seasons": [],
                        }
                    else:
                        if not shows_dict[show_name]["file_path"]:
                            shows_dict[show_name]["file_path"] = (
                                f"/serve-image/{parent_dir}/{file_name}"
                                if asset_folders
                                else f"/serve-image/{file_name}"
                            )
                        if not shows_dict[show_name]["source_path"]:
                            shows_dict[show_name]["source_path"] = file.source_path
                        if not shows_dict[show_name]["file_hash"]:
                            shows_dict[show_name]["file_hash"] = file.file_hash

                if season_match:
                    show_name = (
                        parent_dir_stripped
                        if asset_folders
                        else strip_id(season_match.group("name"))
                    )
                    season_number = int(season_match.group("season"))
                    if show_name not in shows_dict:
                        shows_dict[show_name] = {
                            "file_name": show_name,
                            "file_path": "",
                            "source_path": "",
                            "file_hash": "",
                            "seasons": [],
                        }
                    shows_dict[show_name]["seasons"].append(
                        {
                            "season": season_number,
                            "source_path": file.source_path,
                            "file_hash": file.file_hash,
                            "file_path": (
                                f"/serve-image/{parent_dir}/{file_name}"
                                if asset_folders
                                else f"/serve-image/{file_name}"
                            ),
                        }
                    )
        for show in shows_dict.values():
            show["seasons"].sort(key=lambda s: s["season"])
        # pprint.pprint(shows_dict, width=120)

        sorted_files["shows"] = shows_dict
        sorted_files["movies"] = sorted(
            sorted_files["movies"], key=lambda x: x["file_name"]
        )
        sorted_files["collections"] = sorted(
            sorted_files["collections"], key=lambda x: x["file_name"]
        )
        sorted_files["shows"] = dict(sorted(shows_dict.items(), key=lambda x: x[0]))

        # pprint.pprint(sorted_files["shows"], width=120)

        return jsonify({"success": True, "data": sorted_files})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@poster_renamer.route("/delete-poster", methods=["DELETE"])
def delete_poster():
    try:
        data = request.get_json()
        serve_image_path = data.get("filePath")
        if not serve_image_path:
            return jsonify({"success": False, "message": "File path is required"}), 400
        relative_path = serve_image_path.replace("/serve-image/", "").lstrip("/")
        settings = models.Settings.query.first()
        assets_directory = getattr(settings, "target_path", "").strip()
        if not assets_directory:
            return jsonify(
                {"success": False, "message": "Target path is not configured"}
            ), 500
        file_path = Path(os.path.join(assets_directory, relative_path)).resolve()
        if not str(file_path).startswith(str(Path(assets_directory).resolve())):
            return jsonify({"success": False, "message": "Invalid file path"}), 400

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            database.delete_file_cache_entry(str(file_path))
            return jsonify(
                {"success": True, "message": "Poster deleted successfully."}
            ), 200
        else:
            return jsonify({"success": False, "message": "File does not exist."}), 404

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def get_jobs_data():
    current_jobs = db.session.query(CurrentJobs).all()
    current_jobs_dict = {
        job.job_name: {
            "last_run": job.last_run,
            "next_run": job.next_run,
        }
        for job in current_jobs
    }

    job_history = db.session.query(JobHistory).all()
    job_history_sorted = sorted(job_history, key=lambda job: job.run_time, reverse=True)
    job_history_dict = defaultdict(list)

    for job in job_history_sorted:
        job_history_dict[job.job_name].append(
            {"run_time": job.run_time, "status": job.status, "run_type": job.run_type}
        )

    return {
        "current_jobs": current_jobs_dict,
        "job_history": dict(job_history_dict),
    }


def fetch_unmatched_stats_from_db() -> dict[str, int | str]:
    stats = models.UnmatchedStats.query.get(1)
    if stats:
        grand_total = (
            stats.total_movies
            + stats.total_series
            + stats.total_seasons
            + stats.total_collections
        )
        unmatched_grand_total = (
            stats.unmatched_movies
            + stats.unmatched_series
            + stats.unmatched_seasons
            + stats.unmatched_collections
        )
        percent_complete_movies = (
            100 * (stats.total_movies - stats.unmatched_movies) / stats.total_movies
            if stats.total_movies
            else 0
        )
        percent_complete_shows = (
            100 * (stats.total_series - stats.unmatched_series) / stats.total_series
            if stats.total_series
            else 0
        )
        percent_complete_seasons = (
            100 * (stats.total_seasons - stats.unmatched_seasons) / stats.total_seasons
            if stats.total_seasons
            else 0
        )
        percent_complete_collections = (
            100
            * (stats.total_collections - stats.unmatched_collections)
            / stats.total_collections
            if stats.total_collections
            else 0
        )
        percent_complete_grand_total = (
            100 * (grand_total - unmatched_grand_total) / grand_total
            if grand_total
            else 0
        )
        return {
            "total_movies": stats.total_movies,
            "percent_complete_movies": f"{percent_complete_movies:.2f}%",
            "total_series": stats.total_series,
            "percent_complete_series": f"{percent_complete_shows:.2f}%",
            "total_seasons": stats.total_seasons,
            "percent_complete_seasons": f"{percent_complete_seasons:.2f}%",
            "total_collections": stats.total_collections,
            "percent_complete_collections": f"{percent_complete_collections:.2f}%",
            "grand_total": grand_total,
            "percent_complete_grand_total": f"{percent_complete_grand_total:.2f}%",
            "unmatched_movies": stats.unmatched_movies,
            "unmatched_series": stats.unmatched_series,
            "unmatched_seasons": stats.unmatched_seasons,
            "unmatched_collections": stats.unmatched_collections,
            "unmatched_grand_total": unmatched_grand_total,
        }
    else:
        return {
            "total_movies": 0,
            "percent_complete_movies": "0%",
            "total_series": 0,
            "percent_complete_series": "0%",
            "total_seasons": 0,
            "percent_complete_seasons": "0%",
            "total_collections": 0,
            "percent_complete_collections": "0%",
            "grand_total": 0,
            "percent_complete_grand_total": "0%",
            "unmatched_movies": 0,
            "unmatched_series": 0,
            "unmatched_seasons": 0,
            "unmatched_collections": 0,
            "unmatched_grand_total": 0,
        }


def fetch_unmatched_assets_from_db() -> dict[str, list[dict[str, str | list]]]:
    unmatched_movies = models.UnmatchedMovies.query.all()
    unmatched_shows = models.UnmatchedShows.query.all()
    unmatched_collections = models.UnmatchedCollections.query.all()

    movies = sorted(
        [{"id": movie.id, "title": movie.title} for movie in unmatched_movies],
        key=lambda x: x["title"],
    )
    collections = sorted(
        [
            {"id": collection.id, "title": collection.title}
            for collection in unmatched_collections
        ],
        key=lambda x: x["title"],
    )
    shows = []
    for show in sorted(unmatched_shows, key=lambda x: x.title):
        seasons = [
            {"id": seasons.id, "season": seasons.season} for seasons in show.seasons
        ]
        shows.append(
            {
                "id": show.id,
                "title": show.title,
                "main_poster_missing": show.main_poster_missing,
                "seasons": seasons,
            }
        )

    return {"movies": movies, "shows": shows, "collections": collections}


def fetch_hide_collection_flag():
    settings = models.Settings.query.first()
    if settings:
        return bool(settings.disable_unmatched_collections)
    return False


@poster_renamer.route("/poster-renamer/job-data", methods=["GET"])
def fetch_job_history():
    try:
        jobs = get_jobs_data()
        return jsonify(
            {
                "success": True,
                "jobs": jobs,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@poster_renamer.route("/poster-renamer/unmatched", methods=["GET"])
def fetch_unmatched_assets():
    try:
        unmatched_media = fetch_unmatched_assets_from_db()
        unmatched_counts = fetch_unmatched_stats_from_db()
        disable_collections = fetch_hide_collection_flag()
        return jsonify(
            {
                "success": True,
                "unmatched_media": unmatched_media,
                "unmatched_counts": unmatched_counts,
                "disable_collections": disable_collections,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@poster_renamer.route("/arr-webhook", methods=["POST"])
def recieve_webhook():
    from postarr import app as flask_app
    from postarr import db
    from postarr.models import Settings

    job_name = modules.Settings.POSTER_RENAMERR.value

    run_single_item = Settings.query.with_entities(Settings.run_single_item).scalar()
    if run_single_item is None:
        postarr_logger.error("No settings found or run_single_item is not configured.")
        database.add_job_to_history(job_name, "failed", "webhook")
        database.update_scheduled_job(job_name, None)
        return jsonify({"message": "Settings not configured"}), 500
    if not run_single_item:
        postarr_logger.debug("Single item processing is disabled in settings.")
        database.add_job_to_history(job_name, "skipped (disabled)", "webhook")
        database.update_scheduled_job(job_name, None)
        return jsonify({"message": "Single item processing disabled"}), 403

    webhook_manager = WebhookManager(db.session, postarr_logger)

    try:
        data = request.json
        if not data:
            postarr_logger.error("No data received in the webhook")
            database.add_job_to_history(job_name, "failed", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "No data received"}), 400
        postarr_logger.debug(f"===== Webhook data =====\n{pformat(data, indent=2)}")

        valid_event_types = ["Download", "Grab", "MovieAdded", "SeriesAdd"]
        webhook_event_type = data.get("eventType", "")

        if webhook_event_type == "Test":
            postarr_logger.info("Test event received successfully")
            return jsonify({"message": "OK"}), 200

        if webhook_event_type not in valid_event_types:
            postarr_logger.debug(f"'{webhook_event_type}' is not a valid event type")
            database.add_job_to_history(job_name, "failed", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "Invalid event type"}), 400

        postarr_logger.info(f"Processing event type: {webhook_event_type}")
        item_type = (
            "movie" if "movie" in data else "series" if "series" in data else None
        )
        if not item_type:
            postarr_logger.error(
                "Item type 'movie' or 'series' not found in webhook data"
            )
            database.add_job_to_history(job_name, "failed", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "Invalid webhook data"}), 400

        id = data.get(item_type, {}).get("id", None)
        id = int(id)
        if not id:
            postarr_logger.error(f"Item ID not found for {item_type} in webhook data")
            database.add_job_to_history(job_name, "failed", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "Invalid webhook data"}), 400

        instance = data.get("instanceName", "")
        if not instance:
            postarr_logger.error(
                "Instance name missing from webhook data, please configure in arr settings."
            )
            database.add_job_to_history(job_name, "failed", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "Invalid webhook data"}), 400

        item_path = None

        if item_type == "movie":
            item_path = data.get(item_type, {}).get("folderPath", None)
        elif item_type == "series":
            item_path = data.get(item_type, {}).get("path", None)
            episodes = data.get("episodes", [])
            if episodes:
                episode = episodes[0]
                season_number = episode.get("seasonNumber", None)
                if season_number:
                    item_path = f"{item_path}-Season{season_number}"
                    postarr_logger.debug(
                        f"Found episodes, updating item_path to '{item_path}'"
                    )
                else:
                    postarr_logger.debug(
                        f"No season number found, sticking with item_path= '{item_path}'"
                    )
            else:
                postarr_logger.debug(
                    f"No episode info found, sticking with item_path= '{item_path}'"
                )

        if not item_path:
            postarr_logger.error("Item path missing from webhook data")
            database.add_job_to_history(job_name, "failed", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "Invalid webhook data"}), 400

        new_item = {
            "type": item_type,
            "item_id": id,
            "instance_name": instance,
            "item_path": item_path,
        }

        postarr_logger.debug(f"NEW ITEM = \n{pformat(new_item, indent=2)}")

        is_duplicate = webhook_manager.is_duplicate_webhook(new_item)
        if is_duplicate:
            postarr_logger.debug(f"Duplicate webhook detected: {new_item}")
            database.add_job_to_history(job_name, "skipped (dupe)", "webhook")
            database.update_scheduled_job(job_name, None)
            return jsonify({"message": "Skipped task (duplicate)"}), 200
        else:
            postarr_logger.debug(f"Extracted item: {new_item}")
            result = run_renamer_task(flask_app, webhook_item=new_item)

    except Exception as e:
        postarr_logger.error(
            f"Error retrieving single item from webhook: {e}", exc_info=True
        )
        database.add_job_to_history(job_name, "failed", "webhook")
        return jsonify({"message": "Internal server error"}), 500

    database.add_job_to_history(job_name, "success", "webhook")
    database.update_scheduled_job(job_name, None)
    postarr_logger.debug(f"Returning response: {result}")
    return jsonify(result), 500 if result["success"] is False else 202


@poster_renamer.route("/run-unmatched-job", methods=["POST"])
def run_unmatched():
    from postarr import app as flask_app

    data = request.get_json() or {}
    overrides = data.get("settings", {})
    result = run_unmatched_assets_task(flask_app, overrides=overrides)
    job_name = modules.Settings.UNMATCHED_ASSETS.value

    if result["success"] is False:
        database.add_job_to_history(job_name, "failed", "manual")
    else:
        database.add_job_to_history(job_name, "success", "manual")

    database.update_scheduled_job(job_name, None)
    return jsonify(result), 500 if result["success"] is False else 202


@poster_renamer.route("/run-renamer-job", methods=["POST"])
def run_renamer():
    from postarr import app as flask_app

    data = request.get_json() or {}
    overrides = data.get("settings", {})
    result = run_renamer_task(flask_app, overrides=overrides)
    job_name = modules.Settings.POSTER_RENAMERR.value

    if result["success"] is False:
        database.add_job_to_history(job_name, "failed", "manual")
    else:
        database.add_job_to_history(job_name, "success", "manual")
    return jsonify(result), 500 if result["success"] is False else 202


@poster_renamer.route("/run-border-replace-job", methods=["POST"])
def run_border_replacer():
    from postarr import app as flask_app

    data = request.get_json() or {}
    overrides = data.get("settings", {})
    result = run_border_replacer_task(flask_app, overrides=overrides)
    job_name = modules.Settings.BORDER_REPLACERR.value

    if result["success"] is False:
        database.add_job_to_history(job_name, "failed", "manual")
        database.update_scheduled_job(job_name, None)
        return jsonify(result), 500
    elif result["job_id"] is None:
        database.add_job_to_history(job_name, "success", "manual")
        database.update_scheduled_job(job_name, None)
        return jsonify(result), 200

    database.add_job_to_history(job_name, "success", "manual")
    database.update_scheduled_job(job_name, None)

    return jsonify(result), 202


@poster_renamer.route("/run-plex-upload-job", methods=["POST"])
def run_plex_upload():
    from postarr import app as flask_app

    data = request.get_json() or {}
    overrides = data.get("settings", {})

    result = run_plex_uploaderr_task(flask_app, overrides=overrides)
    job_name = modules.Settings.PLEX_UPLOADERR.value
    if result["success"] is False:
        database.add_job_to_history(job_name, "failed", "manual")
    else:
        database.add_job_to_history(job_name, "success", "manual")

    database.update_scheduled_job(job_name, None)
    return jsonify(result), 500 if result["success"] is False else 202


@poster_renamer.route("/run-drive-sync-job", methods=["POST"])
def run_drive_sync():
    from postarr import app as flask_app

    data = request.get_json() or {}
    overrides = data.get("settings", {})

    result = run_drive_sync_task(flask_app, overrides=overrides)
    job_name = modules.Settings.DRIVE_SYNC.value
    if result["success"] is False:
        database.add_job_to_history(job_name, "failed", "manual")
    else:
        database.add_job_to_history(job_name, "success", "manual")

    database.update_scheduled_job(job_name, None)
    return jsonify(result), 500 if result["success"] is False else 202


@poster_renamer.route("/progress/<job_id>", methods=["GET"])
def get_progress(job_id):
    job_progress = progress_instance.get_progress(job_id)
    if job_progress:
        return jsonify(
            {
                "job_id": job_id,
                "state": job_progress["state"],
                "value": job_progress["value"],
            }
        )
    else:
        return jsonify({"error": "Job not found"}), 404
