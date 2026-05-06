"""Owner notification on new chart calculations.

Posts a small "new chart" notice to a configurable webhook (email via
Resend, Slack/Discord webhook, or any HTTP endpoint that accepts JSON).
Silently no-ops when env vars aren't set so local development never
needs credentials.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error

from app.config import settings

logger = logging.getLogger(__name__)


def notify_new_chart(
    birth_datetime: str,
    location: str,
    zodiac_system: str | None = None,
    house_system: str | None = None,
) -> None:
    if settings.NOTIFY_PROVIDER == "resend":
        _send_resend(birth_datetime, location, zodiac_system, house_system)
    elif settings.NOTIFY_PROVIDER in {"slack", "discord", "webhook"}:
        _send_webhook(birth_datetime, location, zodiac_system, house_system)
    # Else: notifications disabled — quietly skip.


def _format_lines(birth_datetime, location, zodiac_system, house_system) -> list[str]:
    lines = [f"Date / time: {birth_datetime}", f"Location: {location}"]
    if zodiac_system:
        lines.append(f"Zodiac: {zodiac_system}")
    if house_system:
        lines.append(f"House system: {house_system}")
    return lines


def _send_resend(birth_datetime, location, zodiac_system, house_system) -> None:
    if not (settings.RESEND_API_KEY and settings.OWNER_EMAIL):
        return
    payload = {
        "from": settings.NOTIFY_FROM,
        "to": settings.OWNER_EMAIL,
        "subject": "New chart calculated",
        "text": "\n".join(_format_lines(birth_datetime, location, zodiac_system, house_system)),
    }
    _post_json(
        "https://api.resend.com/emails",
        payload,
        {"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
    )


def _send_webhook(birth_datetime, location, zodiac_system, house_system) -> None:
    if not settings.NOTIFY_WEBHOOK_URL:
        return
    text = "New chart calculated\n" + "\n".join(
        _format_lines(birth_datetime, location, zodiac_system, house_system)
    )
    # Slack and Discord both accept {"text": ...} on incoming webhooks.
    _post_json(settings.NOTIFY_WEBHOOK_URL, {"text": text}, {})


def _post_json(url: str, body: dict, extra_headers: dict) -> None:
    headers = {"Content-Type": "application/json", **extra_headers}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status >= 400:
                logger.warning("notify_new_chart non-2xx: %s", resp.status)
    except urllib.error.HTTPError as exc:
        logger.warning("notify_new_chart http error: %s %s", exc.code, exc.reason)
    except Exception as exc:  # noqa: BLE001
        logger.warning("notify_new_chart exception: %s", exc)
