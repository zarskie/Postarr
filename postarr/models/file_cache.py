import json

from sqlalchemy.types import TEXT, TypeDecorator

from postarr import db


class JSONEncodedText(TypeDecorator):
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class FileCache(db.Model):
    __tablename__ = "file_cache"
    file_path = db.Column(db.String, primary_key=True, nullable=False)
    file_name = db.Column(db.String, nullable=True)
    status = db.Column(db.String, nullable=True)
    has_episodes = db.Column(db.Integer, nullable=True)
    has_file = db.Column(db.Integer, nullable=True)
    media_type = db.Column(db.String, nullable=True)
    file_hash = db.Column(db.String, nullable=True)
    original_file_hash = db.Column(db.String, nullable=True)
    source_path = db.Column(db.String, nullable=True)
    border_replaced = db.Column(db.Integer, default=0, nullable=False)
    border_setting = db.Column(db.String, nullable=True)
    custom_color = db.Column(db.String, nullable=True)
    webhook_run = db.Column(db.Integer, nullable=True)
    uploaded_to_libraries = db.Column(JSONEncodedText, default=[], nullable=False)
    uploaded_editions = db.Column(JSONEncodedText, default=[], nullable=False)
    instance = db.Column(db.String, nullable=True)
    arr_id = db.Column(db.Integer, nullable=True)
    tmdb_id = db.Column(db.String, nullable=True)
    imdb_id = db.Column(db.String, nullable=True)
    tvdb_id = db.Column(db.String, nullable=True)


class UnmatchedMovies(db.Model):
    __tablename__ = "unmatched_movies"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, unique=True, nullable=False)
    arr_id = db.Column(db.Integer, nullable=True)
    instance = db.Column(db.String, nullable=True)
    imdb_id = db.Column(db.String, nullable=True)
    tmdb_id = db.Column(db.String, nullable=True)


class UnmatchedCollections(db.Model):
    __tablename__ = "unmatched_collections"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, unique=True, nullable=False)


class UnmatchedShows(db.Model):
    __tablename__ = "unmatched_shows"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, unique=True, nullable=False)
    arr_id = db.Column(db.Integer, nullable=True)
    main_poster_missing = db.Column(db.Integer, default=0, nullable=False)
    instance = db.Column(db.String, nullable=True)
    imdb_id = db.Column(db.String, nullable=True)
    tmdb_id = db.Column(db.String, nullable=True)
    tvdb_id = db.Column(db.String, nullable=True)
    seasons = db.relationship(
        "UnmatchedSeasons", backref="show", cascade="all, delete-orphan", lazy=True
    )


class UnmatchedSeasons(db.Model):
    __tablename__ = "unmatched_seasons"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    show_id = db.Column(
        db.Integer,
        db.ForeignKey("unmatched_shows.id", ondelete="CASCADE"),
        nullable=False,
    )
    season = db.Column(db.String, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("show_id", "season", name="unique_show_season"),
    )


class UnmatchedStats(db.Model):
    __tablename__ = "unmatched_stats"
    id = db.Column(
        db.Integer,
        primary_key=True,
    )
    total_movies = db.Column(db.Integer, default=0, nullable=False)
    total_series = db.Column(db.Integer, default=0, nullable=False)
    total_seasons = db.Column(db.Integer, default=0, nullable=False)
    total_collections = db.Column(db.Integer, default=0, nullable=False)
    unmatched_movies = db.Column(db.Integer, default=0, nullable=False)
    unmatched_series = db.Column(db.Integer, default=0, nullable=False)
    unmatched_seasons = db.Column(db.Integer, default=0, nullable=False)
    unmatched_collections = db.Column(db.Integer, default=0, nullable=False)
