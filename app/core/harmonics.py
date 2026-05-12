"""Rank Cochrane-style harmonic families by total resonance ("hum")
in a chart's aspects table.
"""
from __future__ import annotations

import math
from functools import reduce
from typing import Iterator

import pandas as pd

from app.core.constants import ASPECTS


HARMONIC_NAMES: dict[int, str] = {
    1: "Unity",
    2: "Polarity",
    3: "Trine",
    4: "Square",
    5: "Quintile",
    6: "Sextile",
    7: "Septile",
    8: "Octile",
    9: "Novile",
    10: "Decile",
    11: "Undecile",
    12: "Duodecile",
}

_NAMED_DEFINITIONS: dict[int, str] = {
    1:  "The complete cycle — total union of two planetary forces into one undivided expression.",
    2:  "The axis of opposition — two forces at maximum separation, creating awareness through contrast and the drive toward integration.",
    3:  "The triangle of ease — energy flows freely between planets, producing natural talent, creative grace, and harmonious resonance.",
    4:  "The cross of manifestation — dynamic tension between four points that generates effort, ambition, and the will to build.",
    5:  "The pentagram of creativity — Cochrane's signature of genius; distinctive style, inspired talent, and unique personal expression.",
    6:  "The hexagram of opportunity — cooperative energy that rewards conscious effort with productive connection and mental agility.",
    7:  "The heptagon of fate — irrational, spiritual vibration beyond rational control; karmic threads, prophetic inspiration, and soul destiny.",
    8:  "The octagon of refinement — persistent minor friction that demands precision, discipline, and incremental mastery.",
    9:  "The nonagon of completion — spiritual fulfilment and idealistic wholeness; the soul approaching inner integration.",
    10: "The decagon of skill — subtle creative refinement that mirrors the quintile's mastery through precise, articulate expression.",
    11: "The undecagon of the transcendent — eccentric, anomalous patterns outside conventional frameworks; visionary or otherworldly quality.",
    12: "The dodecagon of adjustment — subtle re-orientation between energies that do not naturally align; growth through ongoing adaptation.",
}


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, math.isqrt(n) + 1, 2):
        if n % i == 0:
            return False
    return True


def _prime_factors(n: int) -> list[int]:
    """Return sorted list of unique prime factors of n."""
    factors: set[int] = set()
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.add(d)
            n //= d
        d += 1
    if n > 1:
        factors.add(n)
    return sorted(factors)


def _definition(h: int) -> str:
    if h in _NAMED_DEFINITIONS:
        return _NAMED_DEFINITIONS[h]
    if _is_prime(h):
        return (
            f"Prime harmonic resonating at {360 / h:.4f}° — an irreducible vibration "
            f"with a unique, undivided spiritual frequency."
        )
    factors = _prime_factors(h)
    factor_str = " × ".join(f"H{p}" for p in factors)
    return (
        f"Composite harmonic ({factor_str}) resonating at {360 / h:.4f}°; "
        f"blends and amplifies the qualities of its prime harmonic factors."
    )


_MAX_HARMONIC = 360
_RANGE = range(1, _MAX_HARMONIC + 1)

VIBRATIONAL_HARMONICS: pd.DataFrame = pd.DataFrame({
    "harmonic":     list(_RANGE),
    "aspect_degree": [round(360 / h, 6) for h in _RANGE],
    "name":         [HARMONIC_NAMES.get(h, f"H{h}") for h in _RANGE],
    "definition":   [_definition(h) for h in _RANGE],
    "prime":        [_is_prime(h) for h in _RANGE],
    # LCM of each harmonic with 360: the smallest degree-count at which this
    # harmonic completes a whole number of cycles within the zodiac circle.
    "lcm_360":      [math.lcm(h, 360) for h in _RANGE],
})



def rank_harmonic_families(aspects_df: pd.DataFrame) -> list[dict]:
    """Return harmonic families ordered by descending resonance.

    Each family score is the sum of ``Closeness`` over every aspect in
    that family — effectively "how much is this harmonic humming in
    this chart". Aspects already include both major and Cochrane
    higher-harmonic types tagged with their fundamental ``Harmonic``.
    """
    if aspects_df is None or aspects_df.empty:
        return []

    asp_lookup = ASPECTS.set_index("Aspect")["Harmonic"].to_dict()
    df = aspects_df.copy()
    df["Harmonic"] = df["Aspect"].map(asp_lookup)
    df = df.dropna(subset=["Harmonic"])
    if df.empty:
        return []
    df["Harmonic"] = df["Harmonic"].astype(int)

    grouped = (
        df.groupby("Harmonic")
          .agg(score=("Closeness", "sum"), count=("Closeness", "size"))
          .reset_index()
          .sort_values(["score", "Harmonic"], ascending=[False, True])
    )

    return [
        {
            "harmonic": int(row.Harmonic),
            "name": HARMONIC_NAMES.get(int(row.Harmonic), f"H{int(row.Harmonic)}"),
            "score": float(row.score),
            "count": int(row.count),
        }
        for row in grouped.itertuples(index=False)
    ]
