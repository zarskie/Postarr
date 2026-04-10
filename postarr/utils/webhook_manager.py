from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from postarr import models


class WebhookManager:
    def __init__(self, db_session: scoped_session, logger):
        self.db_session = db_session
        self.logger = logger

    def is_duplicate_webhook(self, new_item, cache_duration=600) -> bool:
        item_name = Path(new_item["item_path"]).stem

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=cache_duration)

        self.logger.debug(
            "Checking for duplicates for item '%s', type: %s",
            item_name,
            new_item["type"],
        )

        expired = (
            self.db_session.query(models.WebhookCache)
            .filter(models.WebhookCache.timestamp < cutoff)
            .all()
        )
        if expired:
            self.logger.debug(
                "Removing %s expired webhooks: %s",
                len(expired),
                [e.item_name for e in expired],
            )
            for e in expired:
                self.db_session.delete(e)

        duplicate = (
            self.db_session.query(models.WebhookCache)
            .filter_by(item_type=new_item["type"], item_name=item_name)
            .first()
        )
        if duplicate:
            self.logger.debug(
                "Duplicate webhook detected for item '%s', %s",
                item_name,
                new_item["type"],
            )
            return True

        webhook_entry = models.WebhookCache(
            item_type=new_item["type"],  # type: ignore[call-arg]
            item_name=item_name,  # type: ignore[call-arg]
        )

        self.db_session.add(webhook_entry)
        try:
            self.db_session.commit()
            self.logger.debug("New webhook added to cache '%s'", item_name)
        except IntegrityError:
            self.db_session.rollback()
            self.logger.debug(
                "IntegrityError: Duplicate webhook entry attempted for item: %s",
                item_name,
            )
            return True

        return False
