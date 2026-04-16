"""Aspect detection between bodies in a chart.

An aspect is a specific angular relationship (e.g. 90° = square, 120° =
trine) between two bodies, within an allowed tolerance ("orb"). This
module finds all such relationships for the bodies in a chart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.constants import ASPECTS


# Bodies that should never aspect each other:
#   - Asc/Desc and MC/IC are axis pairs (always exactly 180°)
#   - North/South Node are likewise always exactly 180° apart
_AXIS_POINTS: frozenset[str] = frozenset({"Asc", "Desc", "MC", "IC"})
_NODES: frozenset[str] = frozenset({"North Node", "South Node"})


def calculate_aspects(
    df: pd.DataFrame,
    aspects_table: pd.DataFrame = ASPECTS,
) -> pd.DataFrame:
    """Return a DataFrame of aspects between the bodies in ``df``.

    Parameters
    ----------
    df
        DataFrame with at least ``Body`` and ``Longitude (°)`` columns.
        Rows whose ``Body`` contains ``"House Cusp"`` are skipped.
    aspects_table
        Reference table of aspect types, their exact degrees, orbs,
        colors, symbols, and descriptions. Defaults to
        :data:`app.core.constants.ASPECTS`.

    Returns
    -------
    pd.DataFrame
        One row per detected aspect with columns: ``Body1``, ``Body2``,
        ``Aspect``, ``Angle``, ``Degrees``, ``Color``, ``aspect_symbol``,
        ``Description``, ``Closeness``. ``Closeness`` is ``1.0`` at exact
        aspect, dropping linearly to ``0.0`` at the edge of the orb.
    """
    bodies_df = df[~df["Body"].str.contains("House Cusp")].reset_index(drop=True)
    bodies = bodies_df["Body"].tolist()
    longitudes = bodies_df["Longitude (°)"].to_numpy()
    n = len(bodies)

    if n < 2:
        return _empty_result()

    # Pre-extract the aspect table as numpy arrays for tight inner loop
    asp_degrees = aspects_table["Degrees"].to_numpy()
    asp_orbs = aspects_table["Orb"].to_numpy()

    # Build pairwise angle matrix: angle[i, j] = separation between bodies i and j
    diff = np.abs(longitudes[:, None] - longitudes[None, :])
    angles = np.minimum(diff, 360.0 - diff)  # always 0..180

    results: list[dict] = []

    for i in range(n):
        for j in range(i + 1, n):
            # Skip pairs that are structurally fixed
            if bodies[i] in _NODES and bodies[j] in _NODES:
                continue
            if bodies[i] in _AXIS_POINTS and bodies[j] in _AXIS_POINTS:
                continue

            angle = angles[i, j]

            # Find first matching aspect (ordered by importance in table)
            diffs = np.abs(asp_degrees - angle)
            match_idx = np.where(diffs <= asp_orbs)[0]
            if match_idx.size == 0:
                continue

            k = int(match_idx[0])
            row = aspects_table.iloc[k]
            closeness = 1.0 - diffs[k] / asp_orbs[k]

            results.append({
                "Body1": bodies[i],
                "Body2": bodies[j],
                "Aspect": row["Aspect"],
                "Angle": float(angle),
                "Degrees": row["Degrees"],
                "Color": row["Color"],
                "aspect_symbol": row["aspect_symbol"],
                "Description": row["Description"],
                "Closeness": float(closeness),
            })

    if not results:
        return _empty_result()
    return pd.DataFrame(results)


def _empty_result() -> pd.DataFrame:
    """Return an empty DataFrame with the expected schema."""
    return pd.DataFrame(columns=[
        "Body1", "Body2", "Aspect", "Angle", "Degrees",
        "Color", "aspect_symbol", "Description", "Closeness",
    ])


def most_active_bodies(
    df_aspects: pd.DataFrame,
    min_closeness: float = 0.70,
) -> pd.DataFrame:
    """Count how many tight aspects each body participates in.

    Returns a DataFrame sorted descending by aspect count.
    """
    tight = df_aspects[df_aspects["Closeness"] > min_closeness]
    if tight.empty:
        return pd.DataFrame(columns=["Planet", "Aspect Count"])

    counts = pd.concat([tight["Body1"], tight["Body2"]]).value_counts()
    return (
        counts.rename_axis("Planet")
        .reset_index(name="Aspect Count")
    )
