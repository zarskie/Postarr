import json
import os

import requests
from flask import Blueprint, jsonify, request

from daps_webui import db, models
from daps_webui.models.schedule import Schedule

settings = Blueprint("settings", __name__)


@settings.route("/get-drive-presets", methods=["GET"])
def get_drive_presets():
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        file_path = os.path.join(base_dir, "drives.json")
        with open(file_path, "r") as f:
            presets = json.load(f)
        return jsonify({"success": True, "presets": presets})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/add-instance", methods=["POST"])
def add_instance():
    try:
        data = request.get_json()
        instance_type = data.get("type").strip().lower()
        instance_name = data.get("instanceName").strip()
        url = data.get("url").strip().lower()
        api_key = data.get("apiKey").strip()
        if not all([instance_type, instance_name, url, api_key]):
            return jsonify(
                {"success": False, "message": "Missing required fields"}
            ), 400

        if instance_type == "radarr":
            model = models.RadarrInstance
        elif instance_type == "sonarr":
            model = models.SonarrInstance
        elif instance_type == "plex":
            model = models.PlexInstance
        else:
            return jsonify({"success": False, "message": "Invalid instance type"}), 400
        if model.query.filter_by(instance_name=instance_name).first():
            return jsonify(
                {
                    "success": False,
                    "message": f"An instance with the name '{instance_name}' already exists",
                }
            ), 400
        if model.query.filter_by(url=url).first():
            return jsonify(
                {
                    "success": False,
                    "message": "An instance with this URL already exists",
                }
            ), 400
        if model.query.filter_by(api_key=api_key).first():
            return jsonify(
                {
                    "success": False,
                    "message": "An instance with this API key/token already exists",
                }
            ), 400
        new_instance = model(instance_name=instance_name, url=url, api_key=api_key)
        db.session.add(new_instance)
        db.session.commit()
        return jsonify({"success": True, "message": "Instance added successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/add-drive", methods=["POST"])
def add_drive():
    try:
        data = request.get_json()
        drive_name = data.get("driveName").strip().lower()
        drive_id = data.get("driveId").strip()
        drive_type = data.get("driveType", "").strip() or "other"
        friendly_name = data.get("friendlyName", "").strip() or drive_name

        if not all([drive_name, drive_id]):
            return jsonify(
                {"success": False, "message": "Missing required fields"}
            ), 400

        settings = models.Settings.query.first()
        if not settings or not settings.drive_root:
            return jsonify(
                {"success": False, "message": "Root directory not configured"}
            ), 400

        drive_location = f"{settings.drive_root.rstrip('/')}/{drive_name}"

        existing = models.GDrives.query.filter(
            (models.GDrives.drive_name == drive_name)
            | (models.GDrives.drive_id == drive_id)
        ).first()
        if existing:
            return jsonify(
                {"success": False, "message": "Drive name or ID already exists"}
            ), 400

        new_gdrive = models.GDrives(
            drive_type=drive_type,
            drive_name=drive_name,
            drive_id=drive_id,
            friendly_name=friendly_name,
            drive_location=drive_location,
        )
        db.session.add(new_gdrive)
        db.session.commit()
        return jsonify({"success": True, "message": "Drive added successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/update-drive", methods=["PUT"])
def update_drive():
    try:
        data = request.get_json()
        drive_name = data.get("driveName").strip().lower()
        drive_id = data.get("driveId").strip()
        drive_type = data.get("driveType", "").strip() or "other"
        friendly_name = data.get("friendlyName", "").strip() or drive_name

        if not all([drive_name, drive_id]):
            return jsonify(
                {"success": False, "message": "Missing required fields"}
            ), 400

        settings = models.Settings.query.first()
        if not settings or not settings.drive_root:
            return jsonify(
                {"success": False, "message": "Root directory not configured"}
            ), 400

        drive_location = f"{settings.drive_root.rstrip('/')}/{drive_name}"

        drive = models.GDrives.query.get(data.get("id"))
        if not drive:
            return jsonify({"success": False, "message": "Drive not found"}), 404

        existing = (
            models.GDrives.query.filter(
                (models.GDrives.drive_name == drive_name)
                | (models.GDrives.drive_id == drive_id)
            )
            .filter(models.GDrives.id != drive.id)
            .first()
        )
        if existing:
            return jsonify(
                {"success": False, "message": "Drive name or ID already exists"}
            ), 400

        drive.drive_name = drive_name
        drive.drive_id = drive_id
        drive.drive_type = drive_type
        drive.friendly_name = friendly_name
        drive.drive_location = drive_location

        db.session.commit()

        return jsonify({"success": True, "message": "Drive updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/delete-drive", methods=["DELETE"])
def delete_drive():
    try:
        data = request.get_json()
        drive_id = data.get("id")
        if not drive_id:
            return jsonify({"success": False, "message": "Missing drive ID"}), 400

        drive = models.GDrives.query.get(drive_id)
        if not drive:
            return jsonify({"success": False, "message": "Drive not found"}), 404
        db.session.delete(drive)
        db.session.commit()
        return jsonify({"success": True, "message": "Drive deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/delete-instance", methods=["DELETE"])
def delete_instance():
    try:
        data = request.get_json()
        instance_type = data.get("type")
        instance_id = data.get("id")
        if not all([instance_type, instance_id]):
            return jsonify(
                {"success": False, "message": "Missing required fields"}
            ), 400

        if instance_type == "radarr":
            model = models.RadarrInstance
        elif instance_type == "sonarr":
            model = models.SonarrInstance
        elif instance_type == "plex":
            model = models.PlexInstance
        else:
            return jsonify({"success": False, "message": "Invalid instance type"}), 400
        instance = model.query.get(instance_id)
        if not instance:
            return jsonify({"success": False, "message": "Instance not found"}), 404
        db.session.delete(instance)
        db.session.commit()
        return jsonify({"success": True, "message": "Instance deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/update-instance", methods=["PUT"])
def update_instance():
    try:
        data = request.get_json()
        instance_type = data.get("type").strip().lower()
        instance_id = data.get("id")
        instance_name = data.get("instanceName").strip()
        url = data.get("url").strip().lower()
        api_key = data.get("apiKey").strip()
        if not all([instance_type, instance_id, instance_name, url]):
            return jsonify(
                {"success": False, "message": "Missing required fields"}
            ), 400

        if instance_type == "radarr":
            model = models.RadarrInstance
        elif instance_type == "sonarr":
            model = models.SonarrInstance
        elif instance_type == "plex":
            model = models.PlexInstance
        else:
            return jsonify({"success": False, "message": "Invalid instance type"}), 400

        instance = model.query.get(instance_id)
        if not instance:
            return jsonify({"success": False, "message": "Instance not found"}), 404

        if model.query.filter(
            model.instance_name == instance_name, model.id != instance_id
        ).first():
            return jsonify(
                {
                    "success": False,
                    "message": f"An instance with the name '{instance_name}' already exists",
                }
            ), 400
        if model.query.filter(model.url == url, model.id != instance_id).first():
            return jsonify(
                {
                    "success": False,
                    "message": "An instance with this URL already exists",
                }
            ), 400
        if (
            api_key
            and model.query.filter(
                model.api_key == api_key, model.id != instance_id
            ).first()
        ):
            return jsonify(
                {
                    "success": False,
                    "message": "An instance with this API key/token already exists",
                }
            ), 400
        instance.instance_name = instance_name
        instance.url = url
        if api_key:
            instance.api_key = api_key
        db.session.commit()
        return jsonify({"success": True, "message": "Instance updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-plex-libraries", methods=["GET"])
def get_plex_libraries():
    try:
        plex_instances = models.PlexInstance.query.all()
        if not plex_instances:
            return jsonify(
                {"success": False, "message": "No Plex instance configured"}
            ), 400
        all_libraries = []
        for instance in plex_instances:
            try:
                from plexapi.server import PlexServer

                plex = PlexServer(instance.url, instance.api_key)
                libraries = plex.library.sections()
                for lib in libraries:
                    if lib.title not in all_libraries:
                        all_libraries.append(lib.title)
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500
        return jsonify({"success": True, "libraries": all_libraries})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-source-folders", methods=["GET"])
def get_source_folders():
    try:
        poster_root = request.args.get("posterRoot", "").strip()
        if not os.path.exists(poster_root):
            return jsonify(
                {
                    "success": False,
                    "message": f"Directory '{poster_root}' does not exist",
                }
            ), 400
        folders = [
            f
            for f in os.listdir(poster_root)
            if os.path.isdir(os.path.join(poster_root, f))
        ]
        if not folders:
            return jsonify(
                {
                    "success": False,
                    "message": "No subdirectories found in root directory",
                }
            ), 400

        return jsonify({"success": True, "folders": sorted(folders)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-drives", methods=["GET"])
def get_drives():
    try:
        gdrives = models.GDrives.query.all()
        gdrives_list = []
        for drive in gdrives:
            gdrives_list.append(
                {
                    "id": drive.id,
                    "drive_type": drive.drive_type,
                    "drive_name": drive.drive_name,
                    "drive_id": drive.drive_id,
                    "friendly_name": drive.friendly_name,
                    "drive_location": drive.drive_location,
                }
            )

        return jsonify({"success": True, "drives": gdrives_list})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-instances", methods=["GET"])
def get_instances():
    try:
        radarr_instances = models.RadarrInstance.query.all()
        sonarr_instances = models.SonarrInstance.query.all()
        plex_instances = models.PlexInstance.query.all()
        instances = []
        for instance in radarr_instances:
            instances.append(
                {
                    "id": instance.id,
                    "type": "radarr",
                    "name": instance.instance_name,
                    "url": instance.url,
                    "apiKey": instance.api_key,
                }
            )

        for instance in sonarr_instances:
            instances.append(
                {
                    "id": instance.id,
                    "type": "sonarr",
                    "name": instance.instance_name,
                    "url": instance.url,
                    "apiKey": instance.api_key,
                }
            )
        for instance in plex_instances:
            instances.append(
                {
                    "id": instance.id,
                    "type": "plex",
                    "name": instance.instance_name,
                    "url": instance.url,
                    "apiKey": instance.api_key,
                }
            )
        return jsonify({"success": True, "instances": instances})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-schedule/<module_name>", methods=["GET"])
def get_schedule(module_name):
    try:
        schedule = (
            Schedule.query.filter_by(module=module_name)
            .order_by(Schedule.id.desc())
            .first()
        )
        if not schedule:
            return jsonify({"success": True, "data": None})
        return jsonify(
            {
                "success": True,
                "data": {
                    "schedule_type": schedule.schedule_type,
                    "schedule_value": schedule.schedule_value,
                    "next_run": schedule.next_run,
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/delete-schedule/<module_name>", methods=["POST"])
def delete_schedule(module_name):
    try:
        schedule = Schedule.query.filter_by(module=module_name).first()
        if not schedule:
            return jsonify({"success": False, "message": "No schedule found"}), 404

        db.session.delete(schedule)
        db.session.commit()
        reload_scheduler()
        return jsonify({"success": True, "message": "Schedule successfully deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/add-schedule", methods=["POST"])
def add_schedule():
    try:
        data = request.get_json()
        module = data.get("module").strip()
        schedule_type = data.get("scheduleType").strip().lower()
        schedule_value = data.get("scheduleValue").strip()

        if not all([module, schedule_type, schedule_value]):
            return jsonify(
                {"success": False, "message": "Missing required fields"}
            ), 400
        if schedule_type not in ["cron", "interval"]:
            return jsonify({"success": False, "message": "Invalid schedule type"}), 400

        existing_schedule = Schedule.query.filter_by(module=module).first()

        if existing_schedule:
            existing_schedule.schedule_type = schedule_type
            existing_schedule.schedule_value = schedule_value
            message = "Schedule updated successfully!"
        else:
            new_schedule = Schedule(
                module=module,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                next_run="",
            )
            db.session.add(new_schedule)
            message = "Schedule added successfully!"

        db.session.commit()
        reload_scheduler()
        return jsonify({"success": True, "message": message})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/save-poster-renamerr", methods=["POST"])
def save_poster_renamerr():
    try:
        data = request.get_json()
        log_level = data.get("logLevel", "").strip()
        poster_root = data.get("posterRoot", "").strip()
        asset_directory = data.get("assetDirectory", "").strip()
        source_folders = data.get("sourceFolders", [])
        libraries = data.get("libraries", [])
        settings_data = data.get("settings", {})
        border_type = data.get("borderType")
        custom_hex = data.get("customHex")
        if not os.path.exists(poster_root):
            return jsonify(
                {"success": False, "message": "Poster root directory does not exist"}
            ), 404

        existing_settings = models.Settings.query.first()
        if existing_settings:
            existing_settings.log_level_poster_renamer = log_level
            existing_settings.poster_root = poster_root
            existing_settings.target_path = asset_directory
            existing_settings.source_dirs = ",".join(source_folders)
            existing_settings.library_names = ",".join(libraries)
            existing_settings.asset_folders = settings_data.get("assetFolders", False)
            existing_settings.clean_assets = settings_data.get("cleanAssets", False)
            existing_settings.unmatched_assets = settings_data.get(
                "unmatchedAssets", False
            )
            existing_settings.replace_border = settings_data.get("replaceBorder", False)
            existing_settings.run_single_item = settings_data.get("webhookRun", False)
            existing_settings.only_unmatched = settings_data.get("unmatchedOnly", False)
            existing_settings.upload_to_plex = settings_data.get("plexUpload", False)
            existing_settings.match_alt = settings_data.get("matchAltTitles", False)
            existing_settings.drive_sync = settings_data.get("driveSync", False)
            existing_settings.border_setting = border_type
            existing_settings.custom_color = custom_hex
            existing_settings.poster_renamerr_configured = 1
        else:
            new_settings = models.Settings(
                log_level_poster_renamer=log_level,
                poster_root=poster_root,
                target_path=asset_directory,
                source_dirs=",".join(source_folders),
                library_names=",".join(libraries),
                asset_folders=settings_data.get("assetFolders", False),
                clean_assets=settings_data.get("cleanAssets", False),
                unmatched_assets=settings_data.get("unmatchedAssets", False),
                replace_border=settings_data.get("replaceBorder", False),
                run_single_item=settings_data.get("webhookRun", False),
                only_unmatched=settings_data.get("unmatchedOnly", False),
                upload_to_plex=settings_data.get("plexUpload", False),
                match_alt=settings_data.get("matchAltTitles", False),
                drive_sync=settings_data.get("driveSync", False),
                border_setting=border_type,
                custom_color=custom_hex,
                poster_renamerr_configured=1,
            )
            db.session.add(new_settings)
        db.session.commit()
        return jsonify({"success": True, "message": "Settings saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/save-unmatched-assets", methods=["POST"])
def save_unmatched_assets():
    try:
        data = request.get_json()
        log_level = data.get("logLevel", "").strip()
        settings_data = data.get("settings", {})

        existing_settings = models.Settings.query.first()
        if existing_settings:
            existing_settings.log_level_unmatched_assets = log_level
            existing_settings.show_all_unmatched = settings_data.get(
                "showAllUnmatched", False
            )
            existing_settings.disable_unmatched_collections = settings_data.get(
                "hideCollections", False
            )
            existing_settings.unmatched_assets_configured = 1
        else:
            new_settings = models.Settings(
                log_level_unmatched_assets=log_level,
                show_all_unmatched=settings_data.get("showAllUnmatched", False),
                disable_unmatched_collections=settings_data.get(
                    "hideCollections", False
                ),
                unmatched_assets_configured=1,
            )
            db.session.add(new_settings)
        db.session.commit()
        return jsonify({"success": True, "message": "Settings saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/save-plex-uploaderr", methods=["POST"])
def save_plex_uploaderr():
    try:
        data = request.get_json()
        log_level = data.get("logLevel", "").strip()
        settings_data = data.get("settings", {})

        existing_settings = models.Settings.query.first()
        if existing_settings:
            existing_settings.log_level_plex_uploaderr = log_level
            existing_settings.reapply_posters = settings_data.get(
                "reapplyPosters", False
            )
            existing_settings.plex_uploaderr_configured = 1
        else:
            new_settings = models.Settings(
                log_level_plex_uploaderr=log_level,
                reapply_posters=settings_data.get("reapplyPosters", False),
                plex_uploaderr_configured=1,
            )
            db.session.add(new_settings)
        db.session.commit()
        return jsonify({"success": True, "message": "Settings saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/save-rclone-config", methods=["POST"])
def save_rclone_config():
    try:
        data = request.get_json()
        auth_method = data.get("authMethod", "").strip()
        client_id = data.get("clientId", "").strip()
        client_secret = data.get("clientSecret", "").strip()
        oauth_token = data.get("oAuthToken", "").strip()
        service_account = data.get("serviceAccount", "").strip()

        existing_settings = models.RCloneConf.query.first()
        if existing_settings:
            existing_settings.auth_method = auth_method
            existing_settings.client_id = client_id
            existing_settings.client_secret = client_secret
            existing_settings.oauth_token = oauth_token
            existing_settings.service_account = service_account
        else:
            new_settings = models.RCloneConf(
                auth_method=auth_method,
                client_id=client_id,
                client_secret=client_secret,
                oauth_token=oauth_token,
                service_account=service_account,
            )
            db.session.add(new_settings)
        db.session.commit()
        return jsonify({"success": True, "message": "Settings saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/save-drive-sync", methods=["POST"])
def save_drive_sync():
    try:
        data = request.get_json()
        log_level = data.get("logLevel", "").strip()
        root_directory = data.get("rootDirectory", "").strip()
        if not os.path.exists(root_directory):
            return jsonify(
                {"success": False, "message": "Root directory does not exist"}
            ), 404

        existing_settings = models.Settings.query.first()
        if existing_settings:
            existing_settings.log_level_drive_sync = log_level
            existing_settings.drive_root = root_directory
            existing_settings.drive_sync_configured = 1
        else:
            new_settings = models.Settings(
                log_level_drive_sync=log_level,
                drive_root=root_directory,
                drive_sync_configured=1,
            )
            db.session.add(new_settings)
        db.session.commit()
        return jsonify({"success": True, "message": "Settings saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-poster-renamerr", methods=["GET"])
def get_poster_renamerr():
    try:
        settings = models.Settings.query.first()
        if not settings:
            return jsonify({"success": False, "message": "Missing settings data"}), 400

        libraries_list = []
        if settings.library_names:
            libraries_list = [
                name.strip()
                for name in settings.library_names.split(",")
                if name.strip()
            ]
        source_folders_list = []
        if settings.source_dirs:
            source_folders_list = [
                name.strip() for name in settings.source_dirs.split(",") if name.strip()
            ]

        return jsonify(
            {
                "success": True,
                "data": {
                    "is_configured": bool(settings.poster_renamerr_configured)
                    if settings
                    else False,
                    "log_level": settings.log_level_poster_renamer
                    if settings
                    else "info",
                    "poster_root": settings.poster_root if settings else None,
                    "asset_directory": settings.target_path if settings else None,
                    "source_folders": source_folders_list,
                    "libraries": libraries_list,
                    "asset_folders": bool(settings.asset_folders)
                    if settings
                    else False,
                    "clean_assets": bool(settings.clean_assets) if settings else False,
                    "unmatched_assets": bool(settings.unmatched_assets)
                    if settings
                    else False,
                    "replace_border": bool(settings.replace_border)
                    if settings
                    else False,
                    "webhook_run": bool(settings.run_single_item)
                    if settings
                    else False,
                    "unmatched_only": bool(settings.only_unmatched)
                    if settings
                    else False,
                    "plex_upload": bool(settings.upload_to_plex) if settings else False,
                    "match_alt_titles": bool(settings.match_alt) if settings else False,
                    "drive_sync": bool(settings.drive_sync) if settings else False,
                    "border_type": settings.border_setting if settings else None,
                    "custom_hex": settings.custom_color if settings else None,
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-unmatched-assets", methods=["GET"])
def get_unmatched_assets():
    try:
        settings = models.Settings.query.first()
        return jsonify(
            {
                "success": True,
                "data": {
                    "is_configured": settings.unmatched_assets_configured
                    if settings
                    else False,
                    "log_level": settings.log_level_unmatched_assets
                    if settings
                    else "info",
                    "show_all_unmatched": bool(settings.show_all_unmatched)
                    if settings
                    else False,
                    "hide_collections": bool(settings.disable_unmatched_collections)
                    if settings
                    else False,
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-plex-uploaderr", methods=["GET"])
def get_plex_uploaderr():
    try:
        settings = models.Settings.query.first()

        return jsonify(
            {
                "success": True,
                "data": {
                    "is_configured": settings.plex_uploaderr_configured
                    if settings
                    else False,
                    "log_level": settings.log_level_plex_uploaderr
                    if settings
                    else "info",
                    "reapply_posters": bool(settings.reapply_posters)
                    if settings
                    else False,
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@settings.route("/get-drive-sync", methods=["GET"])
def get_drive_sync():
    try:
        rclone_settings = models.RCloneConf.query.first()
        app_settings = models.Settings.query.first()

        return jsonify(
            {
                "success": True,
                "data": {
                    "is_configured": app_settings.drive_sync_configured
                    if app_settings
                    else False,
                    "log_level": app_settings.log_level_drive_sync
                    if app_settings
                    else "info",
                    "root_directory": app_settings.drive_root if app_settings else None,
                    "auth_method": rclone_settings.auth_method
                    if rclone_settings
                    else None,
                    "client_id": rclone_settings.client_id if rclone_settings else None,
                    "client_secret": rclone_settings.client_secret
                    if rclone_settings
                    else None,
                    "oauth_token": rclone_settings.oauth_token
                    if rclone_settings
                    else None,
                    "service_account": rclone_settings.service_account
                    if rclone_settings
                    else None,
                },
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def reload_scheduler():
    from daps_webui import (
        app,
        daps_logger,
        load_schedules_from_db,
        update_next_run_times,
    )

    try:
        load_schedules_from_db(app)
        update_next_run_times(app)
        daps_logger.info("Scheduler reloaded successfully!")
    except Exception as e:
        daps_logger.error(f"Error reloading scheduler: {e}")


@settings.route("/test-connection", methods=["POST"])
def test_connection():
    data = request.get_json()
    url = data.get("url").strip()
    api_key = data.get("apiKey").strip()
    instance_type = data.get("type").strip().lower()
    if instance_type in ["radarr", "sonarr"]:
        headers = {"X-Api-Key": api_key}
    elif instance_type == "plex":
        headers = {"X-Plex-Token": api_key}
    else:
        return jsonify({"success": False, "message": "Invalid instance type"}), 400

    response = None

    try:
        if instance_type == "radarr":
            response = requests.get(
                f"{url}/api/v3/system/status", headers=headers, timeout=5
            )
        elif instance_type == "sonarr":
            response = requests.get(
                f"{url}/api/v3/system/status", headers=headers, timeout=5
            )
        elif instance_type == "plex":
            response = requests.get(
                f"{url}/status/sessions", headers=headers, timeout=5
            )

        if response and response.status_code == 200:
            return jsonify({"success": True, "message": "Connection successful!"})
        else:
            return jsonify({"success": False, "message": "Failed to connect!"}), 400
    except requests.RequestException as e:
        return jsonify({"success": False, "message": str(e)}), 400
