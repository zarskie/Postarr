import os
import re

from flask import Blueprint, jsonify, request, send_from_directory

from postarr import postarr_logger
from postarr.models.settings import Settings

poster_search = Blueprint("poster_search", __name__)
_file_cache = []
_cache_built = False


def normalize(s):
    s = re.sub(r"\{[^}]*\}", "", s)
    s = s.replace("(", "").replace(")", "").replace("-", "")
    return re.sub(r"\s+", " ", s).strip().lower()


def build_cache(root_dir):
    return [
        os.path.join(dirpath, f)
        for dirpath, _, files in os.walk(root_dir)
        for f in files
    ]


def get_cache():
    global _file_cache, _cache_built
    if not _cache_built:
        settings = Settings.query.first()
        if settings and settings.poster_root:
            _file_cache = build_cache(settings.poster_root)
            _cache_built = True
    return _file_cache


@poster_search.route("/search", methods=["GET"])
def search():
    query = normalize(request.args.get("q", "").lower().strip())
    filter_mode = request.args.get("filter", "all")
    if not query or len(query) < 3:
        return jsonify({"results": []})
    cache = get_cache()
    settings = Settings.query.first()
    root = settings.poster_root if settings else ""
    source_dirs = (
        [s.strip() for s in (settings.source_dirs or "").split(",") if s.strip()]
        if settings
        else []
    )
    matched = [
        {
            "filename": os.path.basename(f),
            "path": os.path.relpath(f, root).split(os.sep)[0],
            "full_path": f,
        }
        for f in cache
        if query in normalize(os.path.basename(f).lower())
    ]

    def priority_key(r):
        try:
            return source_dirs.index(r["path"])
        except ValueError:
            return len(source_dirs)

    matched.sort(key=lambda r: (r["path"].lower(), r["filename"].lower()))
    if filter_mode == "enabled":
        matched = [r for r in matched if r["path"] in source_dirs]
    if filter_mode == "priority":
        matched = [r for r in matched if r["path"] in source_dirs]
        matched.sort(key=priority_key)
    if filter_mode == "priority_all":
        matched.sort(key=priority_key)

    return jsonify({"results": matched[:100], "total": len(matched)})


@poster_search.route("/serve-image", methods=["GET"])
def serve_poster_image():
    path = request.args.get("path", "")
    if not path:
        return jsonify({"success": False, "message": "No path provided"}), 400

    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    try:
        return send_from_directory(directory, filename)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
