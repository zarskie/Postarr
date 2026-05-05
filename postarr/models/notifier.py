from postarr import db


class Notifier(db.Model):
    __tablename__ = "notifier"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    enabled = db.Column(db.Integer, default=1, nullable=False)

    def __init__(self, type: str, url: str, enabled: bool = True):
        self.type = type
        self.url = url
        self.enabled = int(enabled)
