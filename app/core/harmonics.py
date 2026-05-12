"""Rank Cochrane-style harmonic families by total resonance ("hum")
in a chart's aspects table.
"""
from __future__ import annotations

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

# Prime harmonics carry an undivided, irreducible vibration — their energy
# cannot be broken into simpler harmonic factors. Non-prime harmonics are
# composites and blend the qualities of their factors.
_PRIME_HARMONICS: frozenset[int] = frozenset({2, 3, 5, 7, 11})

VIBRATIONAL_HARMONICS: pd.DataFrame = pd.DataFrame({
    "harmonic": list(range(1, 13)),
    "aspect_degree": [round(360 / h, 4) for h in range(1, 13)],
    "name": [HARMONIC_NAMES[h] for h in range(1, 13)],
    "definition": [
        "The complete cycle — total union of two planetary forces into one undivided expression.",
        "The axis of opposition — two forces at maximum separation, creating awareness through contrast and the drive toward integration.",
        "The triangle of ease — energy flows freely between planets, producing natural talent, creative grace, and harmonious resonance.",
        "The cross of manifestation — dynamic tension between four points that generates effort, ambition, and the will to build.",
        "The pentagram of creativity — Cochrane's signature of genius; distinctive style, inspired talent, and unique personal expression.",
        "The hexagram of opportunity — cooperative energy that rewards conscious effort with productive connection and mental agility.",
        "The heptagon of fate — irrational, spiritual vibration beyond rational control; karmic threads, prophetic inspiration, and soul destiny.",
        "The octagon of refinement — persistent minor friction that demands precision, discipline, and incremental mastery.",
        "The nonagon of completion — spiritual fulfilment and idealistic wholeness; the soul approaching inner integration.",
        "The decagon of skill — subtle creative refinement that mirrors the quintile's mastery through precise, articulate expression.",
        "The undecagon of the transcendent — eccentric, anomalous patterns outside conventional frameworks; visionary or otherworldly quality.",
        "The dodecagon of adjustment — subtle re-orientation between energies that do not naturally align; growth through ongoing adaptation.",
    ],
    "prime": [h in _PRIME_HARMONICS for h in range(1, 13)],
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
