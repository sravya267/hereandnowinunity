"""Pydantic request/response schemas for the chart API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChartRequest(BaseModel):
    """Input for all chart endpoints."""

    birth_datetime: datetime = Field(
        ...,
        description="Local wall-clock time at place of birth, ISO-8601.",
        examples=["1969-06-14T04:40:00"],
    )
    location: str = Field(
        ...,
        min_length=1,
        description="Geocodable place name (city, or 'City, Country').",
        examples=["Mannheim", "Bhadrachalam, India"],
    )
    zodiac_system: Literal["Tropical", "Sidereal"] = Field(
        default="Tropical",
        description="Zodiac system. Tropical uses Koch houses; "
                    "Sidereal uses Whole Sign with Lahiri Ayanamsa.",
    )
    house_system: Literal[
        "Placidus", "Koch", "Whole Sign", "Equal", "Porphyry",
        "Regiomontanus", "Campanus",
    ] = Field(
        default="Koch",
        description="House system (tropical only). Sidereal charts always use Whole Sign.",
    )


class BirthMomentResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    julian_day_ut: float


class ChartResponse(BaseModel):
    """Full chart as JSON."""

    birth_datetime: datetime
    location: str
    zodiac_system: str
    moment: BirthMomentResponse
    bodies: list[dict[str, Any]]
    aspects: list[dict[str, Any]]
    ayanamsa: float | None = None
    traits: list[dict[str, Any]] | None = None
    patterns: list[dict[str, Any]] | None = None
    harmonics: list[dict[str, Any]] | None = None
