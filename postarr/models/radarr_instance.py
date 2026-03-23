from postarr import db


class RadarrInstance(db.Model):
    __tablename__ = "radarr_instances"
    id = db.Column(db.Integer, primary_key=True)
    instance_name = db.Column(db.String, nullable=True)
    url = db.Column(db.String, nullable=True)
    api_key = db.Column(db.String, nullable=True)

    def __init__(self, instance_name, url, api_key):
        self.instance_name = instance_name
        self.url = url
        self.api_key = api_key
