from postarr import db


class GDrives(db.Model):
    __tablename__ = "gdrives"
    id = db.Column(db.Integer, primary_key=True)
    drive_type = db.Column(db.String, nullable=True)
    drive_name = db.Column(db.String, nullable=True)
    drive_id = db.Column(db.String, nullable=True)
    friendly_name = db.Column(db.String, nullable=True)
    drive_location = db.Column(db.String, nullable=True)

    def __init__(
        self,
        drive_type: str,
        drive_name: str,
        drive_id: str,
        friendly_name: str,
        drive_location: str,
    ) -> None:
        self.drive_type = drive_type
        self.drive_name = drive_name
        self.drive_id = drive_id
        self.friendly_name = friendly_name
        self.drive_location = drive_location
