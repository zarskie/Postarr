from postarr import db


class RCloneConf(db.Model):
    __tablename__ = "rclone"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String, nullable=True)
    oauth_token = db.Column(db.String, nullable=True)
    client_secret = db.Column(db.String, nullable=True)
    service_account = db.Column(db.String, nullable=True)
    auth_method = db.Column(db.String, nullable=True)

    def __init__(
        self,
        client_id=None,
        oauth_token=None,
        client_secret=None,
        service_account=None,
        auth_method=None,
    ) -> None:
        self.client_id = client_id
        self.oauth_token = oauth_token
        self.client_secret = client_secret
        self.service_account = service_account
        self.auth_method = auth_method
