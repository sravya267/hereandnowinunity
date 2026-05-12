"""Harmonic matrix: for every body pair, score resonance against H1-H360.

Produces the data needed for a heatmap of (body pair) x (harmonic) and a
long-form table of matched (body pair, harmonic) hits.

Two tightness measures per (pair, harmonic):
    Tightness   - degrees off from a perfect conjunction in the H-h
                  harmonic chart (low = tight, 0 = exact)
    Tightness%  - same thing as a 0-100% scale relative to OrbLimit
                  (high = tight, 100 = exact)

Method:
    For two planets with longitudes L1, L2 and harmonic h:
        aspect_angle = min(|L1 - L2|, 360 - |L1 - L2|)        # 0..180,
                                                              # the angular
                                                              # gap between
                                                              # the two bodies
        Mod          = (aspect_angle * h) mod 360             # 0..360
        Tightness    = min(Mod, 360 - Mod)                    # 0..180
    The pair forms a conjunction in the H-h chart if Tightness <= OrbLimit.
    OrbLimit at H1 is base_orb; narrows with h via orb_formula.
    Tightness% = 100 * (1 - Tightness / OrbLimit) — 100 at exact, 0 at edge.
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

    Cell value is Tightness% (0..100) at which that pair resonates with that
    harmonic. 0 means the pair does not form a conjunction in the H-h chart;
    100 means an exact conjunction in that chart.

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

        mod = (aspect_angle * harmonics) % 360
        tightness = np.minimum(mod, 360 - mod)

        hit_mask = tightness <= orbs
        tightness_pct = np.where(hit_mask, 100.0 * (1.0 - tightness / orbs), 0.0)

        pair_labels.append(f"{b1} – {b2}")
        rows.append(tightness_pct)

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
    min_tightness_pct: float = 0.0,
) -> pd.DataFrame:
    """Return long-form hits: ``Body1, Body2, Harmonic, AspectAngle, Mod,
    Tightness, OrbLimit, Tightness%``.

    Tightness    - degrees off from exact in the H-h chart (low = tight).
    Tightness%   - same as 0..100 scale of OrbLimit (high = tight).

    Only rows where the pair resonates (Tightness% >= ``min_tightness_pct``)
    are included. Sorted by Tightness% descending.
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

        mod = (aspect_angle * harmonics) % 360
        tightness = np.minimum(mod, 360 - mod)

        hit_idx = np.where(tightness <= orbs)[0]
        for k in hit_idx:
            tightness_pct = 100.0 * (1.0 - tightness[k] / orbs[k])
            if tightness_pct < min_tightness_pct:
                continue
            records.append({
                "Body1": b1,
                "Body2": b2,
                "Harmonic": int(harmonics[k]),
                "AspectAngle": round(float(aspect_angle), 4),
                "Mod": round(float(mod[k]), 4),
                "Tightness": round(float(tightness[k]), 4),
                "OrbLimit": round(float(orbs[k]), 4),
                "Tightness%": round(float(tightness_pct), 2),
            })

    if not records:
        return pd.DataFrame(columns=[
            "Body1", "Body2", "Harmonic", "AspectAngle",
            "Mod", "Tightness", "OrbLimit", "Tightness%",
        ])
    out = pd.DataFrame(records)
    return out.sort_values(["Tightness%", "Harmonic"], ascending=[False, True]).reset_index(drop=True)


def rank_harmonics_from_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a heatmap matrix into per-harmonic resonance metrics.

    Returns one row per harmonic with two separate columns:
      - PairCount:     how many body pairs resonate at that harmonic
      - BestTightness%: the tightest hit (max Tightness%, 0..100)

    Sorted by PairCount desc, then BestTightness% desc.
    """
    if matrix.empty:
        return pd.DataFrame(columns=["Harmonic", "PairCount", "BestTightness%"])

    count = (matrix > 0).sum(axis=0)
    best = matrix.max(axis=0)
    out = pd.DataFrame({
        "Harmonic": [int(c[1:]) for c in matrix.columns],
        "PairCount": count.values,
        "BestTightness%": best.values.round(2),
    })
    return out.sort_values(
        ["PairCount", "BestTightness%"], ascending=[False, False]
    ).reset_index(drop=True)
