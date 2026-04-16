"""High-level chart assembly.

This module ties geocoding, ephemeris calculation, and aspect detection
together into a single :func:`compute_chart` call that returns everything
the API and visualization layers need.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import numpy as np
import pandas as pd
import swisseph as swe

from app.core.aspects import calculate_aspects
from app.core.constants import PLANETS
from app.core.ephemeris import (
    ZodiacSystem,
    calculate_house_cusps,
    calculate_planetary_positions,
    determine_house,
    extract_cusp_number,
)
from app.core.geocoding import BirthMoment, resolve


@dataclass(frozen=True)
class Chart:
    """A computed natal chart."""

    birth_datetime: datetime
    location_name: str
    moment: BirthMoment
    zodiac_system: ZodiacSystem
    bodies: pd.DataFrame      # planets, nodes, angles, house cusps
    aspects: pd.DataFrame     # pairwise aspects


def compute_chart(
    birth_datetime: datetime,
    location_name: str,
    zodiac_system: ZodiacSystem = "Tropical",
) -> Chart:
    """Compute a complete natal chart for the given birth moment.

    Parameters
    ----------
    birth_datetime
        Naive local wall-clock time at the place of birth.
    location_name
        Human-readable place name (geocoded via Nominatim).
    zodiac_system
        ``"Tropical"`` (Koch houses) or ``"Sidereal"`` (Whole Sign,
        Lahiri Ayanamsa).
    """
    moment = resolve(birth_datetime, location_name)

    # Flags for Swiss Ephemeris
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    if zodiac_system == "Sidereal":
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        flags |= swe.FLG_SIDEREAL

    positions = calculate_planetary_positions(moment.julian_day_ut, flags)
    houses = calculate_house_cusps(
        moment.julian_day_ut,
        moment.latitude,
        moment.longitude,
        zodiac_system,
    )

    df = pd.DataFrame(positions + houses)
    df["Sys"] = zodiac_system

    # Attach planet symbols/colors
    df = df.merge(PLANETS, left_on="Body", right_on="Planet", how="left")
    df.drop(columns="Planet", inplace=True)

    # House assignment
    df["House"] = df.apply(
        lambda row: (
            determine_house(row["Longitude (°)"], houses)
            if "House Cusp" not in row["Body"]
            else extract_cusp_number(row["Body"])
        ),
        axis=1,
    )
    df["House"] = df["House"].apply(
        lambda x: str(int(x)) if pd.notnull(x) and x != -1 else ""
    )

    # Rotation so the Descendant sits at 0° in plot coordinates
    desc_row = df.loc[df["Body"] == "Desc", "Longitude (°)"]
    rotation_deg = float(desc_row.iloc[0]) if not desc_row.empty else 0.0
    df["Rotated_Pos"] = df["Longitude (°)"] - rotation_deg

    # Direct / retrograde motion
    df["Motion"] = df["Speed (°/day)"].apply(
        lambda s: "D" if s > 0 else "R" if s < 0 else ""
    )

    # Pre-compute unit-circle coordinates for plotting
    rad = np.deg2rad(df["Rotated_Pos"])
    df["rad_rot_x"] = np.cos(rad)
    df["rad_rot_y"] = np.sin(rad)

    aspects_df = calculate_aspects(df)

    return Chart(
        birth_datetime=birth_datetime,
        location_name=location_name,
        moment=moment,
        zodiac_system=zodiac_system,
        bodies=df,
        aspects=aspects_df,
    )
