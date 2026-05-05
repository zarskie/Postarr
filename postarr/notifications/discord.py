import os
from datetime import datetime, timezone

import requests

from .base import BaseNotifier, NotificationEvent

_TITLES = {
    NotificationEvent.RUN_START: "Run started",
    NotificationEvent.RUN_END: "Run completed",
    NotificationEvent.RUN_ERROR: "Run Error",
    NotificationEvent.RENAME_SUMMARY: "Rename Summary",
    NotificationEvent.UPLOAD_SUMMARY: "Upload Summary",
    NotificationEvent.WEBHOOK_ITEM_NOT_FOUND: "Webhook Item Not Found",
}


class DiscordNotifier(BaseNotifier):
    def _build_description(self, event: NotificationEvent, kwargs: dict) -> str:
        if event == NotificationEvent.RENAME_SUMMARY:
            lines = [
                f"**Movies:** {kwargs.get('copied_movies', 0)}",
                f"**Collections:** {kwargs.get('copied_collections', 0)}",
                f"**Series:** {kwargs.get('copied_series', 0)}",
            ]
            for label, key in [
                ("Movies", "movie_results"),
                ("Collections", "collection_results"),
                ("Series", "series_results"),
            ]:
                results = kwargs.get(key, [])
                if results:
                    lines.append(f"\n**{label}**")
                    for r in results[:10]:
                        from_short = "/".join(r["from"].split("/")[-2:])
                        if kwargs.get("asset_folders"):
                            to_short = "/".join(r["to"].split("/")[-2:])
                        else:
                            to_short = r["to"].split("/")[-1]
                        lines.append(f"`{from_short}`\n↳ `{to_short}`")
                    if len(results) > 10:
                        lines.append(f"*...and {len(results) - 10} more*")
            description = "\n".join(lines)
            return description[:4096]
        if event == NotificationEvent.UPLOAD_SUMMARY:
            upload_stats = kwargs.get("upload_stats", {})
            if not upload_stats:
                return "Nothing was uploaded."
            return "\n".join(
                f"**{library}:** {count} poster(s)"
                for library, count in upload_stats.items()
            )
        return kwargs.get("message", "")

    def send(self, event: NotificationEvent, **kwargs) -> None:
        version = os.environ.get("VERSION", "dev")
        payload = {
            "embeds": [
                {
                    "title": f"{kwargs.get('module', 'Postarr')} — {_TITLES.get(event, event.value)}",
                    "description": self._build_description(event, kwargs),
                    "color": kwargs.get("color", 3066993),
                    "footer": {"text": f"Postarr v{version} by monster"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        try:
            r = requests.post(self.url, json=payload, timeout=5)
            r.raise_for_status()
        except Exception:
            self.logger.warning(
                "Discord notification failed for event %s", event.value, exc_info=True
            )
