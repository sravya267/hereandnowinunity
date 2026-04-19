"""Reference data: zodiac signs, planets, aspect types.

These tables are static and shared across all chart calculations.
Keeping them as module-level constants means they are built once at
import time rather than on every request.
"""
from __future__ import annotations

import pandas as pd
import swisseph as swe


# ---------------------------------------------------------------------------
# Zodiac signs
# ---------------------------------------------------------------------------
SIGN_NAMES: list[str] = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

ZODIAC_INFO: pd.DataFrame = pd.DataFrame({
    "Zodiac Name": SIGN_NAMES,
    "Symbol": ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"],
    "Element": [
        "fire", "earth", "air", "water",
        "fire", "earth", "air", "water",
        "fire", "earth", "air", "water",
    ],
    "Start Angle (°)": [i * 30 for i in range(12)],
    "Color": [
        "red", "green", "yellow", "lightblue",
        "red", "green", "yellow", "lightblue",
        "red", "green", "yellow", "lightblue",
    ],
    "Modality": [
        "Cardinal", "Fixed", "Mutable",
        "Cardinal", "Fixed", "Mutable",
        "Cardinal", "Fixed", "Mutable",
        "Cardinal", "Fixed", "Mutable",
    ],
})


# ---------------------------------------------------------------------------
# Planets and points
# ---------------------------------------------------------------------------
PLANETS: pd.DataFrame = pd.DataFrame({
    "Planet": [
        "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
        "Uranus", "Neptune", "Pluto", "Chiron", "North Node", "South Node",
    ],
    "Symbol": ["☉", "☾", "☿", "♀", "♂", "♃", "♄", "♅", "♆", "♇", "⚷", "☊", "☋"],
    "Color": [
        "#F8F71A", "#b0c4de", "#34F520", "#F871F0", "#FB1406", "#C4C321",
        "#3421A1", "#A01414", "#68D6F3", "#D3E0E4", "#808080", "#696969", "#696969",
    ],
})

# Swiss Ephemeris body IDs. South Node is computed as (North Node + 180°) mod 360.
PLANET_IDS: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Chiron": swe.CHIRON,
    "North Node": swe.TRUE_NODE,
}


# ---------------------------------------------------------------------------
# Aspects
# ---------------------------------------------------------------------------
# Orbs are doubled vs. the raw values to match the notebook's behaviour.
_BASE_ORBS = [5, 5, 5, 4, 2, 3, 1, 2, 2, 1, 1]

ASPECTS: pd.DataFrame = pd.DataFrame({
    "Degrees": [180.0, 120.0, 90.0, 72.0, 60.0, 360 / 7, 45.0, 40.0, 36.0, 360 / 11, 30.0],
    "Aspect": [
        "Opposition", "Trine", "Square", "Quintile", "Sextile", "Septile",
        "Semi-square", "Novile", "Decile", "Undecile", "Semi-sextile",
    ],
    "Orb": [o * 2 for o in _BASE_ORBS],
    "Description": [
        "Indicates tension, conflict, or balance between opposing forces.",
        "Harmonious aspect that facilitates natural flow and ease.",
        "Challenging aspect causing tension and requiring effort to overcome.",
        "Linked to creativity and innovation, enhancing unique talents.",
        "Beneficial and harmonious, enhancing compatibility and productivity.",
        "Associated with spiritual or karmic influences and subtle destinies.",
        "Indicates minor challenges and friction, requiring adjustments.",
        "Connected to spiritual insights, deep wisdom, or enlightenment.",
        "Related to subtle talents and creative nuances.",
        "Reflects minor but significant interactions, often nuanced or specialized.",
        "Mildly harmonious or challenging, offers slight opportunities.",
    ],
    "Color": [
        "#FF0000", "#0000FF", "#FF4500", "#1E90FF", "#4682B4", "#87CEEB",
        "#FF6347", "#ADD8E6", "#B0E0E6", "#5F9EA0", "#00BFFF",
    ],
    "aspect_symbol": ["☍", "△", "□", "⚼", "✶", "⚤", "☌", "⭘", "⭑", "⭒", "⚹"],
})


NAKSHATRA_NAMES: list[str] = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

NAKSHATRA_LORDS: list[str] = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury", "Ketu", "Venus",
    "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn",
    "Mercury", "Ketu", "Venus", "Sun", "Moon",
    "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
]


def degree_to_sign(degree: float) -> str:
    """Map an ecliptic longitude (0–360°) to its zodiac sign name."""
    return SIGN_NAMES[int(degree // 30) % 12]


def degree_to_nakshatra(degree: float) -> dict:
    """Map a sidereal longitude to its nakshatra, pada, and lord."""
    idx = int(degree / (360 / 27)) % 27
    pada = int((degree % (360 / 27)) / (360 / 108)) + 1
    return {"Nakshatra": NAKSHATRA_NAMES[idx], "Pada": pada, "Lord": NAKSHATRA_LORDS[idx]}
