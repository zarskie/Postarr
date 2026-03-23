from postarr import db


class WebhookCache(db.Model):
    __tablename__ = "webhook_cache"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    item_type = db.Column(db.String, nullable=False)
    item_name = db.Column(db.String, nullable=False)
    timestamp = db.Column(
        db.DateTime, nullable=False, default=db.func.current_timestamp()
    )
    __table_args__ = (
        db.UniqueConstraint("item_type", "item_name", name="unique_item_type_name"),
    )
