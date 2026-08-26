"""Geocoding and time-zone resolution.

Turns a human-readable location plus local wall-clock time into the
(latitude, longitude, Julian day UT) triple that Swiss Ephemeris expects.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

import pytz
import swisseph as swe
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from app.config import settings


_geolocator = Nominatim(user_agent=settings.GEOCODER_USER_AGENT, timeout=10)
_tz_finder = TimezoneFinder()
_GEOCODE_RETRIES = 3


@dataclass(frozen=True)
class BirthMoment:
    """Resolved birth moment in a form ready for ephemeris calculation."""

    latitude: float
    longitude: float
    timezone: str
    julian_day_ut: float


class LocationNotFound(ValueError):
    """Raised when the geocoder cannot resolve a location name."""


@lru_cache(maxsize=512)
def _geocode(location_name: str) -> tuple[float, float]:
    last_error: GeocoderServiceError | None = None
    for attempt in range(_GEOCODE_RETRIES):
        try:
            location = _geolocator.geocode(location_name)
            break
        except GeocoderServiceError as exc:
            last_error = exc
            if attempt < _GEOCODE_RETRIES - 1:
                time.sleep(1 + attempt)
    else:
        raise LocationNotFound(
            f"Location lookup timed out after {_GEOCODE_RETRIES} attempts "
            f"for {location_name!r}. Please try again."
        ) from last_error

    if location is None:
        raise LocationNotFound(f"Could not geocode location: {location_name!r}")
    return location.latitude, location.longitude


@lru_cache(maxsize=512)
def _find_tz(lat: float, lon: float) -> str:
    tz_name = _tz_finder.timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        raise LocationNotFound(
            f"Could not determine time zone for ({lat}, {lon})"
        )
    return tz_name


def resolve(birth_datetime: datetime, location_name: str) -> BirthMoment:
    lat, lon = _geocode(location_name)
    tz_name = _find_tz(lat, lon)

    local_dt = pytz.timezone(tz_name).localize(birth_datetime)
    utc_dt = local_dt.astimezone(pytz.utc)

    julian_day = swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600,
    )

    return BirthMoment(
        latitude=lat,
        longitude=lon,
        timezone=tz_name,
        julian_day_ut=julian_day,
    )
