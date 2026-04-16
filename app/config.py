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


class Settings:
    """Application settings loaded from environment variables."""

    # Paths
    EPHE_PATH: str = os.getenv("EPHE_PATH", str(ROOT_DIR / "ephe"))
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


settings = Settings()
