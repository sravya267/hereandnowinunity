"""Harmonic matrix: for every body pair, score resonance against H1-H360.

Produces the data needed for a heatmap of (body pair) x (harmonic) closeness,
plus a long-form table of matched (body pair, harmonic) hits.

Method (standard vibrational astrology):
    For two planets with longitudes L1, L2 and harmonic h:
        aspect_angle = min(|L1 - L2|, 360 - |L1 - L2|)        # 0..180,
                                                              # the angular
                                                              # gap between
                                                              # the two bodies
        hc_angle     = (aspect_angle * h) mod 360
        hc_orb       = min(hc_angle, 360 - hc_angle)          # 0..180
    The pair forms a conjunction in the H-h chart if hc_orb <= ORB(h).
    Orb tightens with harmonic: ORB(h) = base_orb / sqrt(h).
    Closeness = 1 - hc_orb / ORB(h), so 1.0 at exact, 0.0 at the edge.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from app.core.orbs import DEFAULT_BASE_ORB, DEFAULT_FORMULA, OrbFormula, orb_limit


# Bodies that are structurally fixed (always exactly 180° apart) — skip
_AXIS_POINTS: frozenset[str] = frozenset({"Asc", "Desc", "MC", "IC"})
_NODES: frozenset[str] = frozenset({"North Node", "South Node"})


def _skip_pair(b1: str, b2: str) -> bool:
    if b1 in _NODES and b2 in _NODES:
        return True
    if b1 in _AXIS_POINTS and b2 in _AXIS_POINTS:
        return True
    return False


def compute_harmonic_matrix(
    bodies_df: pd.DataFrame,
    max_harmonic: int = 360,
    base_orb: float = DEFAULT_BASE_ORB,
    orb_formula: OrbFormula = DEFAULT_FORMULA,
) -> pd.DataFrame:
    """Return wide matrix: rows = body pairs, columns = H1..H{max_harmonic}.

    Cell value is the closeness (0..1) at which that pair resonates with that
    harmonic. 0 means the pair does not form a conjunction in the H-h chart.

    Parameters
    ----------
    bodies_df
        DataFrame with ``Body`` and ``Longitude (°)`` columns (same shape as
        the input to :func:`app.core.aspects.calculate_aspects`).
    max_harmonic
        Highest harmonic to evaluate (inclusive). Default 360.
    base_orb
        Orb at H1 in natal-chart degrees. Default 8°.
    orb_formula
        ``"sqrt"`` (default), ``"linear"``, or ``"fixed"``. See
        :mod:`app.core.orbs`.
    """
    df = bodies_df[~bodies_df["Body"].str.contains("House Cusp", na=False)]
    df = df.dropna(subset=["Longitude (°)"]).reset_index(drop=True)
    bodies = df["Body"].tolist()
    longitudes = df["Longitude (°)"].to_numpy()

    harmonics = np.arange(1, max_harmonic + 1)
    orbs = orb_limit(harmonics, base_orb=base_orb, formula=orb_formula)

    pair_labels: list[str] = []
    rows: list[np.ndarray] = []

    for i, j in combinations(range(len(bodies)), 2):
        b1, b2 = bodies[i], bodies[j]
        if _skip_pair(b1, b2):
            continue

        diff = abs(longitudes[i] - longitudes[j]) % 360
        aspect_angle = min(diff, 360 - diff)

        hc_angle = (aspect_angle * harmonics) % 360
        hc_orb = np.minimum(hc_angle, 360 - hc_angle)

        hit_mask = hc_orb <= orbs
        closeness = np.where(hit_mask, 1.0 - hc_orb / orbs, 0.0)

        pair_labels.append(f"{b1} – {b2}")
        rows.append(closeness)

    if not rows:
        return pd.DataFrame(columns=[f"H{h}" for h in harmonics])

    matrix = pd.DataFrame(
        np.vstack(rows),
        index=pair_labels,
        columns=[f"H{h}" for h in harmonics],
    )
    matrix.index.name = "Pair"
    return matrix


def compute_harmonic_long(
    bodies_df: pd.DataFrame,
    max_harmonic: int = 360,
    base_orb: float = DEFAULT_BASE_ORB,
    orb_formula: OrbFormula = DEFAULT_FORMULA,
    min_closeness: float = 0.0,
) -> pd.DataFrame:
    """Return long-form hits: ``Body1, Body2, Harmonic, AspectAngle, Mod, ...``.

    Only rows where the pair actually resonates with the harmonic (closeness
    >= ``min_closeness``) are included. Sorted by Closeness descending.
    """
    df = bodies_df[~bodies_df["Body"].str.contains("House Cusp", na=False)]
    df = df.dropna(subset=["Longitude (°)"]).reset_index(drop=True)
    bodies = df["Body"].tolist()
    longitudes = df["Longitude (°)"].to_numpy()

    harmonics = np.arange(1, max_harmonic + 1)
    orbs = orb_limit(harmonics, base_orb=base_orb, formula=orb_formula)

    records: list[dict] = []
    for i, j in combinations(range(len(bodies)), 2):
        b1, b2 = bodies[i], bodies[j]
        if _skip_pair(b1, b2):
            continue

        diff = abs(longitudes[i] - longitudes[j]) % 360
        aspect_angle = min(diff, 360 - diff)

        hc_angle = (aspect_angle * harmonics) % 360
        hc_orb = np.minimum(hc_angle, 360 - hc_angle)

        hit_idx = np.where(hc_orb <= orbs)[0]
        for k in hit_idx:
            closeness = 1.0 - hc_orb[k] / orbs[k]
            if closeness < min_closeness:
                continue
            records.append({
                "Body1": b1,
                "Body2": b2,
                "Harmonic": int(harmonics[k]),
                "AspectAngle": round(float(aspect_angle), 4),
                "Mod": round(float(hc_angle[k]), 4),
                "HCOrb": round(float(hc_orb[k]), 4),
                "OrbLimit": round(float(orbs[k]), 4),
                "Closeness": round(float(closeness), 4),
            })

    if not records:
        return pd.DataFrame(columns=[
            "Body1", "Body2", "Harmonic", "AspectAngle",
            "Mod", "HCOrb", "OrbLimit", "Closeness",
        ])
    out = pd.DataFrame(records)
    return out.sort_values(["Closeness", "Harmonic"], ascending=[False, True]).reset_index(drop=True)


def rank_harmonics_from_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a heatmap matrix into per-harmonic resonance scores.

    Returns one row per harmonic with the total closeness summed across
    all body pairs, plus the number of pairs that hit it.
    """
    if matrix.empty:
        return pd.DataFrame(columns=["Harmonic", "Score", "PairCount"])

    score = matrix.sum(axis=0)
    count = (matrix > 0).sum(axis=0)
    out = pd.DataFrame({
        "Harmonic": [int(c[1:]) for c in matrix.columns],
        "Score": score.values,
        "PairCount": count.values,
    })
    return out.sort_values("Score", ascending=False).reset_index(drop=True)
