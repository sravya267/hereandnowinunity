"""Owner notification on new chart calculations.

Sends a small "new chart" notice via one of:
- "gmail":    SMTP via smtp.gmail.com using a Google App Password
              (no third-party services — sender is your own Gmail account)
- "resend":   Resend HTTP API
- "slack" |
  "discord" |
  "webhook":  POST {"text": ...} to NOTIFY_WEBHOOK_URL

Silently no-ops when env vars aren't set so local development never
needs credentials.
"""
from __future__ import annotations

import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def notify_new_chart(
    birth_datetime: str,
    location: str,
    zodiac_system: str | None = None,
    house_system: str | None = None,
) -> None:
    lines = _format_lines(birth_datetime, location, zodiac_system, house_system)
    _dispatch("New chart calculated", lines)


def notify_new_synastry(
    person_a_datetime: str,
    person_a_location: str,
    person_b_datetime: str,
    person_b_location: str,
) -> None:
    lines = [
        "Person A:",
        *("  " + line for line in _format_lines(person_a_datetime, person_a_location)),
        "Person B:",
        *("  " + line for line in _format_lines(person_b_datetime, person_b_location)),
    ]
    _dispatch("New synastry chart calculated", lines)


def _format_lines(birth_datetime, location, zodiac_system=None, house_system=None) -> list[str]:
    lines = [f"Date / time: {birth_datetime}", f"Location: {location}"]
    if zodiac_system:
        lines.append(f"Zodiac: {zodiac_system}")
    if house_system:
        lines.append(f"House system: {house_system}")
    return lines


def _dispatch(subject: str, lines: list[str]) -> None:
    if settings.NOTIFY_PROVIDER == "gmail":
        _send_gmail(subject, lines)
    elif settings.NOTIFY_PROVIDER == "resend":
        _send_resend(subject, lines)
    elif settings.NOTIFY_PROVIDER in {"slack", "discord", "webhook"}:
        _send_webhook(subject, lines)
    # Else: notifications disabled — quietly skip.


def _send_gmail(subject: str, lines: list[str]) -> None:
    if not (settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD and settings.OWNER_EMAIL):
        return
    msg = EmailMessage()
    msg["From"] = settings.GMAIL_USER
    msg["To"] = settings.OWNER_EMAIL
    msg["Subject"] = subject
    msg.set_content("\n".join(lines))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("notify gmail exception: %s", exc)


def _send_resend(subject: str, lines: list[str]) -> None:
    if not (settings.RESEND_API_KEY and settings.OWNER_EMAIL):
        return
    payload = {
        "from": settings.NOTIFY_FROM,
        "to": settings.OWNER_EMAIL,
        "subject": subject,
        "text": "\n".join(lines),
    }
    _post_json(
        "https://api.resend.com/emails",
        payload,
        {"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
    )


def _send_webhook(subject: str, lines: list[str]) -> None:
    if not settings.NOTIFY_WEBHOOK_URL:
        return
    text = subject + "\n" + "\n".join(lines)
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
                logger.warning("notify non-2xx: %s", resp.status)
    except urllib.error.HTTPError as exc:
        logger.warning("notify http error: %s %s", exc.code, exc.reason)
    except Exception as exc:  # noqa: BLE001
        logger.warning("notify exception: %s", exc)
