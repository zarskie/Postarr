from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from postarr.models.webhook_cache import WebhookCache


class WebhookManager:
    def __init__(self, db_session: scoped_session, logger):
        self.db_session = db_session
        self.logger = logger

    def is_duplicate_webhook(self, new_item, cache_duration=600) -> bool:
        item_name = Path(new_item["item_path"]).stem

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=cache_duration)

        self.logger.debug(
            f"Checking for duplicates for item: {item_name}, type: {new_item['type']}"
        )

        expired_count = (
            self.db_session.query(WebhookCache)
            .filter(WebhookCache.timestamp < cutoff)
            .delete()
        )
        self.logger.debug(f"Expired webhookes removed: {expired_count}")

        duplicate = (
            self.db_session.query(WebhookCache)
            .filter_by(item_type=new_item["type"], item_name=item_name)
            .first()
        )
        if duplicate:
            self.logger.debug(
                f"Duplicate webhook detected for item: {item_name}, type: {new_item['type']}"
            )
            return True

        webhook_entry = WebhookCache(
            item_type=new_item["type"],
            item_name=item_name,
        )

        self.db_session.add(webhook_entry)
        try:
            self.db_session.commit()
            self.logger.debug(f"New webhook added to cache: {item_name}")
        except IntegrityError:
            self.db_session.rollback()
            self.logger.debug(
                f"IntegrityError: Duplicate webhook entry attempted for item: {item_name}"
            )
            return True

        return False
