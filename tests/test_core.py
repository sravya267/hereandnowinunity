"""Smoke tests for the core calculation layers.

These tests don't require network access or ephemeris files. They
exercise the pure-Python logic: sign mapping, aspect orb matching, and
input validation.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.core.aspects import calculate_aspects, most_active_bodies
from app.core.constants import ASPECTS, degree_to_sign


def test_degree_to_sign_boundaries():
    assert degree_to_sign(0.0) == "Aries"
    assert degree_to_sign(29.999) == "Aries"
    assert degree_to_sign(30.0) == "Taurus"
    assert degree_to_sign(359.999) == "Pisces"


def test_degree_to_sign_wraps():
    # 360° should wrap back to Aries
    assert degree_to_sign(360.0) == "Aries"


def test_aspects_detects_exact_opposition():
    df = pd.DataFrame([
        {"Body": "Sun", "Longitude (°)": 10.0},
        {"Body": "Moon", "Longitude (°)": 190.0},
    ])
    result = calculate_aspects(df, ASPECTS)
    assert len(result) == 1
    assert result.iloc[0]["Aspect"] == "Opposition"
    assert result.iloc[0]["Closeness"] == pytest.approx(1.0)


def test_aspects_detects_exact_trine():
    df = pd.DataFrame([
        {"Body": "Sun", "Longitude (°)": 0.0},
        {"Body": "Jupiter", "Longitude (°)": 120.0},
    ])
    result = calculate_aspects(df, ASPECTS)
    assert (result["Aspect"] == "Trine").any()


def test_aspects_skips_house_cusps():
    df = pd.DataFrame([
        {"Body": "House Cusp 1", "Longitude (°)": 0.0},
        {"Body": "House Cusp 7", "Longitude (°)": 180.0},
    ])
    result = calculate_aspects(df, ASPECTS)
    assert result.empty


def test_aspects_skips_node_pair():
    # Nodes are always 180° apart by construction; should not count as
    # an opposition
    df = pd.DataFrame([
        {"Body": "North Node", "Longitude (°)": 50.0},
        {"Body": "South Node", "Longitude (°)": 230.0},
    ])
    result = calculate_aspects(df, ASPECTS)
    assert result.empty


def test_aspects_skips_axis_pair():
    df = pd.DataFrame([
        {"Body": "Asc", "Longitude (°)": 0.0},
        {"Body": "Desc", "Longitude (°)": 180.0},
        {"Body": "MC", "Longitude (°)": 90.0},
        {"Body": "IC", "Longitude (°)": 270.0},
    ])
    result = calculate_aspects(df, ASPECTS)
    assert result.empty


def test_most_active_empty_input():
    empty = pd.DataFrame(columns=[
        "Body1", "Body2", "Aspect", "Angle", "Degrees",
        "Color", "aspect_symbol", "Description", "Closeness",
    ])
    result = most_active_bodies(empty)
    assert result.empty
    assert list(result.columns) == ["Planet", "Aspect Count"]
