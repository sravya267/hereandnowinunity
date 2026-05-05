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
