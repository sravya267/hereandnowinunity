"""Swiss Ephemeris calculations: planetary positions and house cusps."""
from __future__ import annotations

from typing import Literal

import swisseph as swe

from app.config import settings
from app.core.constants import PLANET_IDS, degree_to_sign


ZodiacSystem = Literal["Tropical", "Sidereal"]


# Initialize ephemeris path once at import time
swe.set_ephe_path(settings.EPHE_PATH)


def calculate_planetary_positions(julian_day: float, flags: int) -> list[dict]:
    """Return positions for all configured planets plus North & South Node.

    Each entry contains longitude, latitude, right ascension, declination,
    daily speed, and zodiac sign.
    """
    positions: list[dict] = []

    for name, body_id in PLANET_IDS.items():
        pos, _ = swe.calc_ut(julian_day, body_id, flags)
        positions.append({
            "Body": name,
            "Longitude (°)": pos[0],
            "Latitude (°)": pos[1],
            "RA (°)": pos[2],
            "Declination (°)": pos[3],
            "Speed (°/day)": pos[4],
            "Sign": degree_to_sign(pos[0]),
        })

    # South Node = North Node + 180°
    north_node = next((p for p in positions if p["Body"] == "North Node"), None)
    if north_node is not None:
        south_lon = (north_node["Longitude (°)"] + 180) % 360
        positions.append({
            "Body": "South Node",
            "Longitude (°)": south_lon,
            "Latitude (°)": north_node["Latitude (°)"],
            "RA (°)": (north_node["RA (°)"] + 180) % 360,
            "Declination (°)": -north_node["Declination (°)"],
            "Speed (°/day)": north_node["Speed (°/day)"],
            "Sign": degree_to_sign(south_lon),
        })

    return positions


def calculate_house_cusps(
    julian_day: float,
    latitude: float,
    longitude: float,
    system: ZodiacSystem,
) -> list[dict]:
    """Return house cusps plus Ascendant, MC, Descendant, and IC.

    Tropical charts use the Koch house system. Sidereal charts use Whole
    Sign houses with the Lahiri Ayanamsa.
    """
    if system == "Tropical":
        house_positions, ascmc = swe.houses(julian_day, latitude, longitude, b"K")
    else:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayanamsa = swe.get_ayanamsa(julian_day)
        house_positions, ascmc = swe.houses(julian_day, latitude, longitude, b"W")
        ascmc = [(angle - ayanamsa) % 360 for angle in ascmc[:4]]
        asc_sign = int(ascmc[0] // 30)
        house_positions = [(asc_sign * 30 + i * 30) % 360 for i in range(12)]

    cusps: list[dict] = [
        {
            "Body": f"House Cusp {i + 1}",
            "Longitude (°)": pos,
            "Sign": degree_to_sign(pos),
        }
        for i, pos in enumerate(house_positions)
    ]

    asc = ascmc[0]
    mc = ascmc[1]
    cusps.extend([
        {"Body": "Asc", "Longitude (°)": asc, "Sign": degree_to_sign(asc)},
        {"Body": "MC", "Longitude (°)": mc, "Sign": degree_to_sign(mc)},
        {
            "Body": "Desc",
            "Longitude (°)": (asc + 180) % 360,
            "Sign": degree_to_sign((asc + 180) % 360),
        },
        {
            "Body": "IC",
            "Longitude (°)": (mc + 180) % 360,
            "Sign": degree_to_sign((mc + 180) % 360),
        },
    ])
    return cusps


def determine_house(planet_degree: float, house_cusps: list[dict]) -> int:
    """Return the house number (1–12) a given longitude falls into."""
    for i in range(12):
        start = house_cusps[i]["Longitude (°)"]
        end = house_cusps[(i + 1) % 12]["Longitude (°)"]
        if start < end and start <= planet_degree < end:
            return i + 1
        if start > end and (start <= planet_degree or planet_degree < end):
            return i + 1
    return -1


def extract_cusp_number(body: str) -> str | None:
    """Pull the house number out of a ``'House Cusp N'`` label."""
    if "House Cusp" in body:
        return body.split()[-1]
    return None
