from postarr import db


class NotifierEvent(db.Model):
    __tablename__ = "notifier_event"
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String, nullable=False)
    module = db.Column(db.String, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("event", "module", name="uq_notifier_event_module"),
    )

    def __init__(self, event: str, module: str):
        self.event = event
        self.module = module
