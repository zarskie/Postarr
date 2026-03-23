from postarr import db


class Schedule(db.Model):
    __tablename__ = "schedule"
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String, nullable=True)
    schedule_type = db.Column(db.String, nullable=True)
    schedule_value = db.Column(db.String, nullable=True)
    next_run = db.Column(db.String, nullable=True)

    def __init__(
        self,
        module: str,
        schedule_type: str,
        schedule_value: str,
        next_run: str,
    ) -> None:
        self.module = module
        self.schedule_type = schedule_type
        self.schedule_value = schedule_value
        self.next_run = next_run
