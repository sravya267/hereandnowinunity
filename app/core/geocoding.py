"""Geocoding and time-zone resolution.

Turns a human-readable location plus local wall-clock time into the
(latitude, longitude, Julian day UT) triple that Swiss Ephemeris expects.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytz
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from app.config import settings


# Module-level singletons. Nominatim and TimezoneFinder are expensive to
# build and safe to reuse across requests.
_geolocator = Nominatim(user_agent=settings.GEOCODER_USER_AGENT)
_tz_finder = TimezoneFinder()


@dataclass(frozen=True)
class BirthMoment:
    """Resolved birth moment in a form ready for ephemeris calculation."""

    latitude: float
    longitude: float
    timezone: str
    julian_day_ut: float


class LocationNotFound(ValueError):
    """Raised when the geocoder cannot resolve a location name."""


def resolve(birth_datetime: datetime, location_name: str) -> BirthMoment:
    """Resolve a naive local birth datetime + place into a ``BirthMoment``.

    Parameters
    ----------
    birth_datetime
        Naive ``datetime`` representing local wall-clock time at the place
        of birth.
    location_name
        Any string Nominatim can geocode, e.g. ``"Mannheim"`` or
        ``"Bhadrachalam, India"``.

    Raises
    ------
    LocationNotFound
        If the geocoder returns no match.
    """
    location = _geolocator.geocode(location_name)
    if location is None:
        raise LocationNotFound(f"Could not geocode location: {location_name!r}")

    lat, lon = location.latitude, location.longitude
    tz_name = _tz_finder.timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        raise LocationNotFound(
            f"Could not determine time zone for ({lat}, {lon})"
        )

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
