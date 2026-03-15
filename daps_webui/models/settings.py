from daps_webui import db


class Settings(db.Model):
    __tablename__ = "settings_table"
    id = db.Column(db.Integer, primary_key=True)
    log_level_unmatched_assets = db.Column(db.String, default="info", nullable=False)
    log_level_poster_renamer = db.Column(db.String, default="info", nullable=False)
    log_level_plex_uploaderr = db.Column(db.String, default="info", nullable=False)
    log_level_border_replacerr = db.Column(db.String, default="info", nullable=False)
    log_level_drive_sync = db.Column(db.String, default="info", nullable=False)
    poster_root = db.Column(db.String, nullable=True)
    drive_root = db.Column(db.String, nullable=True)
    target_path = db.Column(db.String, nullable=True)
    source_dirs = db.Column(db.String, nullable=True)
    library_names = db.Column(db.String, nullable=True)
    asset_folders = db.Column(db.Integer, default=0, nullable=False)
    clean_assets = db.Column(db.Integer, default=0, nullable=False)
    unmatched_assets = db.Column(db.Integer, default=0, nullable=False)
    replace_border = db.Column(db.Integer, default=0, nullable=False)
    border_setting = db.Column(db.String, nullable=True)
    custom_color = db.Column(db.String, nullable=True)
    run_single_item = db.Column(db.Integer, default=0, nullable=False)
    only_unmatched = db.Column(db.Integer, default=0, nullable=False)
    upload_to_plex = db.Column(db.Integer, default=0, nullable=False)
    match_alt = db.Column(db.Integer, default=0, nullable=False)
    drive_sync = db.Column(db.Integer, default=0, nullable=False)
    reapply_posters = db.Column(db.Integer, default=0, nullable=False)
    show_all_unmatched = db.Column(db.Integer, default=0, nullable=False)
    disable_unmatched_collections = db.Column(db.Integer, default=0, nullable=False)
    poster_renamerr_configured = db.Column(db.Integer, default=0, nullable=False)
    unmatched_assets_configured = db.Column(db.Integer, default=0, nullable=False)
    plex_uploaderr_configured = db.Column(db.Integer, default=0, nullable=False)
    drive_sync_configured = db.Column(db.Integer, default=0, nullable=False)

    def __init__(
        self,
        poster_root=None,
        drive_root=None,
        target_path=None,
        source_dirs=None,
        library_names=None,
        log_level_unmatched_assets="info",
        log_level_poster_renamer="info",
        log_level_plex_uploaderr="info",
        log_level_border_replacerr="info",
        log_level_drive_sync="info",
        asset_folders=False,
        clean_assets=False,
        unmatched_assets=False,
        replace_border=False,
        run_single_item=False,
        only_unmatched=False,
        upload_to_plex=False,
        match_alt=False,
        drive_sync=False,
        reapply_posters=False,
        show_all_unmatched=False,
        disable_unmatched_collections=False,
        border_setting=None,
        custom_color=None,
        poster_renamerr_configured=0,
        unmatched_assets_configured=0,
        plex_uploaderr_configured=0,
        drive_sync_configured=0,
    ):
        self.poster_root = poster_root
        self.drive_root = drive_root
        self.target_path = target_path
        self.source_dirs = source_dirs
        self.library_names = library_names
        self.asset_folders = asset_folders
        self.clean_assets = clean_assets
        self.unmatched_assets = unmatched_assets
        self.replace_border = replace_border
        self.run_single_item = run_single_item
        self.only_unmatched = only_unmatched
        self.upload_to_plex = upload_to_plex
        self.match_alt = match_alt
        self.drive_sync = drive_sync
        self.reapply_posters = reapply_posters
        self.show_all_unmatched = show_all_unmatched
        self.disable_unmatched_collections = disable_unmatched_collections
        self.border_setting = border_setting
        self.custom_color = custom_color
        self.log_level_poster_renamer = log_level_poster_renamer
        self.log_level_plex_uploaderr = log_level_plex_uploaderr
        self.log_level_border_replacerr = log_level_border_replacerr
        self.log_level_drive_sync = log_level_drive_sync
        self.log_level_unmatched_assets = log_level_unmatched_assets
        self.poster_renamerr_configured = poster_renamerr_configured
        self.unmatched_assets_configured = unmatched_assets_configured
        self.plex_uploaderr_configured = plex_uploaderr_configured
        self.drive_sync_configured = drive_sync_configured
