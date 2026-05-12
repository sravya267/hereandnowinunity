"""Harmonic matrix: for every body pair, score resonance against H1-H360.

Produces the data needed for a heatmap of (body pair) x (harmonic) and a
long-form table of matched (body pair, harmonic) hits.

Two tightness measures per (pair, harmonic):
    Tightness   - degrees off nearest exact aspect in the NATAL chart
                  (low = tight, 0 = exact).  This is the remainder after
                  dividing the aspect_angle by the harmonic's step (360/h):
                      r = aspect_angle mod (360/h)
                      Tightness = min(r, 360/h - r)
    HCTightness - same orb scaled to the harmonic chart (Tightness × h).
                  Used internally for the orb check; exposed for reference.
    Tightness%  - 0-100 scale relative to OrbLimit (high = tight, 100 = exact)

Method:
    For two planets with longitudes L1, L2 and harmonic h:
        aspect_angle = min(|L1 - L2|, 360 - |L1 - L2|)   # 0..180
        step         = 360 / h                             # harmonic step
        r            = aspect_angle mod step               # remainder
        Tightness    = min(r, step - r)                    # 0..step/2
        HCTightness  = Tightness × h                       # in H-h chart space
    The pair resonates with harmonic h if HCTightness <= OrbLimit.
    OrbLimit at H1 is base_orb; narrows with h via orb_formula.
    Tightness% = 100 * (1 - HCTightness / OrbLimit) — 100 at exact, 0 at edge.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd

from app.core.orbs import DEFAULT_BASE_ORB, DEFAULT_FORMULA, OrbFormula, orb_limit


# Bodies whose pairs are structurally fixed — skipped in pair computation
_AXIS_POINTS: frozenset[str] = frozenset({"Asc", "Desc", "MC", "IC"})
_NODES: frozenset[str] = frozenset({"North Node", "South Node"})

# Bodies whose pairs inflate harmonic counts without personal meaning
_IMPERSONAL: frozenset[str] = _AXIS_POINTS | _NODES


def _skip_pair(b1: str, b2: str) -> bool:
    """Skip pairs that are always exactly 180° apart by definition."""
    if b1 in _NODES and b2 in _NODES:
        return True
    if b1 in _AXIS_POINTS and b2 in _AXIS_POINTS:
        return True
    return False


def _is_personal_pair(b1: str, b2: str) -> bool:
    """True if at least one body in the pair is a planet (not axis/node)."""
    return not (b1 in _IMPERSONAL and b2 in _IMPERSONAL)


# ---------------------------------------------------------------------------
# Prime factorisation helpers
# ---------------------------------------------------------------------------

def prime_factors(n: int) -> list[int]:
    """Return the prime factors of n (with repetition), e.g. 12 → [2, 2, 3]."""
    factors: list[int] = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


def factor_label(n: int) -> str:
    """Human-readable prime factorisation, e.g. 12 → '2² × 3', 7 → 'prime'."""
    factors = prime_factors(n)
    if len(factors) == 1:
        return "prime"
    counts = Counter(factors)
    parts = []
    for p in sorted(counts):
        exp = counts[p]
        parts.append(f"{p}²" if exp == 2 else f"{p}³" if exp == 3 else f"{p}^{exp}" if exp > 3 else str(p))
    return " × ".join(parts)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_harmonic_matrix(
    bodies_df: pd.DataFrame,
    max_harmonic: int = 360,
    base_orb: float = DEFAULT_BASE_ORB,
    orb_formula: OrbFormula = DEFAULT_FORMULA,
) -> pd.DataFrame:
    """Return wide matrix: rows = body pairs, columns = H1..H{max_harmonic}.

    Cell value is Tightness% (0..100) at which that pair resonates with that
    harmonic. 0 means the pair does not resonate; 100 means exact.

    Parameters
    ----------
    bodies_df
        DataFrame with ``Body`` and ``Longitude (°)`` columns.
    max_harmonic
        Highest harmonic to evaluate (inclusive). Default 360.
    base_orb
        Orb at H1 in natal-chart degrees. Default 8°.
    orb_formula
        ``"sqrt"`` (default), ``"linear"``, or ``"fixed"``.
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

        step = 360.0 / harmonics
        r = aspect_angle % step
        tightness = np.minimum(r, step - r)
        hc_tightness = tightness * harmonics

        hit_mask = hc_tightness <= orbs
        tightness_pct = np.where(hit_mask, 100.0 * (1.0 - hc_tightness / orbs), 0.0)

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
    """Return long-form hits: one row per (pair, harmonic) resonance.

    Columns
    -------
    Body1, Body2     - the two bodies in the pair
    Harmonic         - harmonic number h
    Factors          - prime factorisation label (e.g. '3²', '2 × 7', 'prime')
    AspectAngle      - angular separation between the two bodies (0..180°)
    Tightness        - natal-chart orb: degrees off nearest exact aspect of h
                       = aspect_angle mod (360/h), folded to 0..180/h
    HCTightness      - same orb in harmonic-chart degrees (Tightness × h)
    OrbLimit         - maximum HCTightness allowed for a hit at this h
    Tightness%       - 0-100 closeness score (100 = exact, 0 = at orb edge)
    Personal         - True if at least one body is a planet (not axis/node)

    Sorted by Tightness% descending.
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

        step = 360.0 / harmonics
        r = aspect_angle % step
        tightness = np.minimum(r, step - r)
        hc_tightness = tightness * harmonics

        hit_idx = np.where(hc_tightness <= orbs)[0]
        for k in hit_idx:
            tightness_pct = 100.0 * (1.0 - hc_tightness[k] / orbs[k])
            if tightness_pct < min_tightness_pct:
                continue
            h = int(harmonics[k])
            records.append({
                "Body1": b1,
                "Body2": b2,
                "Harmonic": h,
                "Factors": factor_label(h),
                "AspectAngle": round(float(aspect_angle), 4),
                "Tightness": round(float(tightness[k]), 4),
                "HCTightness": round(float(hc_tightness[k]), 4),
                "OrbLimit": round(float(orbs[k]), 4),
                "Tightness%": round(float(tightness_pct), 2),
                "Personal": _is_personal_pair(b1, b2),
            })

    if not records:
        return pd.DataFrame(columns=[
            "Body1", "Body2", "Harmonic", "Factors", "AspectAngle",
            "Tightness", "HCTightness", "OrbLimit", "Tightness%", "Personal",
        ])
    out = pd.DataFrame(records)
    return out.sort_values(["Tightness%", "Harmonic"], ascending=[False, True]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def rank_harmonics(
    long_df: pd.DataFrame,
    personal_only: bool = True,
) -> pd.DataFrame:
    """Aggregate long-form hits into one row per harmonic.

    Parameters
    ----------
    long_df
        Output of :func:`compute_harmonic_long`.
    personal_only
        If True (default), exclude pairs where both bodies are axis/node
        points. This prevents structural axis pairs from inflating counts.

    Returns
    -------
    DataFrame with columns:

    Harmonic         - harmonic number
    Factors          - prime factorisation (e.g. '3²', '2 × 7', 'prime')
    Name             - harmonic name from vibrational_harmonics.csv
    PairCount        - number of resonating pairs
    Tightest         - natal orb of the closest pair (degrees)
    Pairs            - comma-separated ``Body1–Body2 X.XXX°`` entries
    NatalMeaning     - natal chart interpretation from CSV
    TransitMeaning   - transit interpretation from CSV
    HarmonyMeaning   - synastry/harmony interpretation from CSV
    Source           - citation source from CSV
    """
    from app.core.harmonics import VIBRATIONAL_HARMONICS

    df = long_df[long_df["Personal"]] if personal_only else long_df

    if df.empty:
        return pd.DataFrame(columns=[
            "Harmonic", "Factors", "Name", "PairCount", "Tightest", "Pairs",
            "NatalMeaning", "TransitMeaning", "HarmonyMeaning", "Source",
        ])

    vh = VIBRATIONAL_HARMONICS.set_index("harmonic")[
        ["name", "natal_definition", "transit_definition", "harmony_definition", "source"]
    ]

    rows = []
    for h, group in df.groupby("Harmonic"):
        group = group.sort_values("Tightness")
        pairs_str = ",  ".join(
            f"{r['Body1']}–{r['Body2']} {r['Tightness']:.3f}°"
            for _, r in group.iterrows()
        )
        info = vh.loc[h] if h in vh.index else {}
        rows.append({
            "Harmonic": int(h),
            "Factors": group["Factors"].iloc[0],
            "Name": info.get("name", "") if isinstance(info, dict) else str(info["name"]),
            "PairCount": len(group),
            "Tightest": round(float(group["Tightness"].min()), 4),
            "Pairs": pairs_str,
            "NatalMeaning": info.get("natal_definition", "") if isinstance(info, dict) else str(info["natal_definition"]),
            "TransitMeaning": info.get("transit_definition", "") if isinstance(info, dict) else str(info["transit_definition"]),
            "HarmonyMeaning": info.get("harmony_definition", "") if isinstance(info, dict) else str(info["harmony_definition"]),
            "Source": info.get("source", "") if isinstance(info, dict) else str(info["source"]),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["PairCount", "Tightest"], ascending=[False, True])
        .reset_index(drop=True)
    )


def rank_harmonics_from_matrix(
    matrix: pd.DataFrame,
    base_orb: float = DEFAULT_BASE_ORB,
    orb_formula: OrbFormula = DEFAULT_FORMULA,
) -> pd.DataFrame:
    """Aggregate a heatmap matrix into per-harmonic resonance info.

    Prefer :func:`rank_harmonics` (works from the long-form output and
    supports personal_only filtering). This function is kept for callers
    that already have the wide matrix.

    Returns one row per harmonic with: Harmonic, Factors, PairCount, Pairs.
    Sorted by PairCount desc, then tightest pair asc.
    """
    if matrix.empty:
        return pd.DataFrame(columns=["Harmonic", "Factors", "PairCount", "Pairs"])

    rows = []
    for col in matrix.columns:
        h = int(col[1:])
        orb_at_h = float(orb_limit(h, base_orb=base_orb, formula=orb_formula))
        series = matrix[col]
        hits = series[series > 0]
        # HCTightness = orb_at_h * (1 - pct/100); Tightness = HCTightness / h
        hits_hc = (orb_at_h * (1.0 - hits / 100.0)).sort_values()
        count = len(hits_hc)
        pairs_str = ",  ".join(
            f"{pair} {hc/h:.3f}°"
            for pair, hc in hits_hc.items()
        )
        rows.append({
            "Harmonic": h,
            "Factors": factor_label(h),
            "PairCount": count,
            "Pairs": pairs_str,
            "_top": float(hits_hc.iloc[0]) if count else float("inf"),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(["PairCount", "_top"], ascending=[False, True])
        .drop(columns="_top")
        .reset_index(drop=True)
    )
