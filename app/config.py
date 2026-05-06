"""Application configuration.

All paths and tunable parameters live here so nothing is hardcoded in
business logic. Values come from environment variables with sensible
defaults for local development.
"""
from __future__ import annotations

import os
from pathlib import Path


# Repo root = parent of the `app` package directory
ROOT_DIR = Path(__file__).resolve().parent.parent


def _find_ephe_path() -> str:
    candidates = [
        os.getenv("EPHE_PATH"),
        "/app/ephe",
        str(ROOT_DIR / "ephe"),
    ]
    for p in candidates:
        if p and Path(p).is_dir() and any(Path(p).glob("*.se1")):
            return p
    return os.getenv("EPHE_PATH", str(ROOT_DIR / "ephe"))


class Settings:
    """Application settings loaded from environment variables."""

    EPHE_PATH: str = _find_ephe_path()
    PERSONALITIES_CSV: str = os.getenv(
        "PERSONALITIES_CSV",
        str(ROOT_DIR / "app" / "data" / "ai_personalities.csv"),
    )

    # Geocoding
    GEOCODER_USER_AGENT: str = os.getenv("GEOCODER_USER_AGENT", "astro-chart/1.0")

    # Chart rendering defaults
    CIRCLE_1: float = 2.5
    CIRCLE_SPACING: float = 0.5

    # Aspect detection
    ASPECT_ORB_MULTIPLIER: int = 2  # matches original notebook (aspects['Orb'] *= 2)

    # CORS (comma-separated list; "*" allows everything for local dev)
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Owner notifications on new chart calculations.
    # NOTIFY_PROVIDER: "" (disabled, default), "resend", "slack", "discord", "webhook"
    NOTIFY_PROVIDER: str = os.getenv("NOTIFY_PROVIDER", "").lower()
    # For provider=resend
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    OWNER_EMAIL: str = os.getenv("OWNER_EMAIL", "")
    NOTIFY_FROM: str = os.getenv("NOTIFY_FROM", "onboarding@resend.dev")
    # For provider=slack/discord/webhook
    NOTIFY_WEBHOOK_URL: str = os.getenv("NOTIFY_WEBHOOK_URL", "")


settings = Settings()
