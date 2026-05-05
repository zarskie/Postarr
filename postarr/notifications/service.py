from .base import NotificationEvent
from .discord import DiscordNotifier

_REGISTRY = {"discord": DiscordNotifier}


def notify_all(event: NotificationEvent, **kwargs) -> None:
    from postarr import app, db, postarr_logger
    from postarr.models import Notifier, NotifierEvent

    module = kwargs.get("module", "")

    with app.app_context():
        subscribed = (
            db.session.execute(
                db.select(NotifierEvent).where(
                    NotifierEvent.event == event.value,
                    NotifierEvent.module == module,
                )
            )
            .scalars()
            .first()
        )
        if not subscribed:
            return

        notifiers = (
            db.session.execute(db.select(Notifier).where(Notifier.enabled == 1))
            .scalars()
            .all()
        )
        for notifier in notifiers:
            cls = _REGISTRY.get(notifier.type)
            if cls is None:
                postarr_logger.warning(
                    "Unknown notifier type %r, skipping", notifier.type
                )
                continue
            cls(url=notifier.url, logger=postarr_logger).send(event, **kwargs)
