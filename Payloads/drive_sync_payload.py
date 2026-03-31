from dataclasses import dataclass


@dataclass(slots=True)
class Payload:
    log_level: int
    client_id: str
    oauth_token: str
    client_secret: str
    service_account: str
    gdrives: list
