"""Cross-chart (synastry) calculations."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.constants import ASPECTS
from app.core.orbs import DEFAULT_BASE_ORB, DEFAULT_FORMULA, OrbFormula, orb_limit


def calculate_cross_aspects(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    base_orb: float = DEFAULT_BASE_ORB,
    orb_formula: OrbFormula = DEFAULT_FORMULA,
) -> pd.DataFrame:
    """Aspects between every planet in chart A and every planet in chart B (no A-A or B-B pairs)."""
    bodies_a = df_a[~df_a["Body"].str.contains("House Cusp")].reset_index(drop=True)
    bodies_b = df_b[~df_b["Body"].str.contains("House Cusp")].reset_index(drop=True)

    asp_degrees = ASPECTS["Degrees"].to_numpy()
    asp_harmonics = ASPECTS["Harmonic"].to_numpy()
    asp_orbs = orb_limit(asp_harmonics, base_orb=base_orb, formula=orb_formula)

    results = []
    for _, row_a in bodies_a.iterrows():
        for _, row_b in bodies_b.iterrows():
            lon_a = row_a["Longitude (°)"]
            lon_b = row_b["Longitude (°)"]
            diff = abs(lon_a - lon_b) % 360
            angle = min(diff, 360.0 - diff)

            diffs = np.abs(asp_degrees - angle)
            match_idx = np.where(diffs <= asp_orbs)[0]
            if match_idx.size == 0:
                continue

            k = int(match_idx[0])
            asp_row = ASPECTS.iloc[k]
            closeness = float(1.0 - diffs[k] / asp_orbs[k])

            results.append({
                "Body1": row_a["Body"],
                "Body2": row_b["Body"],
                "Aspect": asp_row["Aspect"],
                "Angle": float(angle),
                "Degrees": asp_row["Degrees"],
                "OrbLimit": float(asp_orbs[k]),
                "Color": asp_row["Color"],
                "aspect_symbol": asp_row["aspect_symbol"],
                "Description": asp_row["Description"],
                "Closeness": closeness,
            })

    if not results:
        return pd.DataFrame(columns=["Body1","Body2","Aspect","Angle","Degrees","OrbLimit","Color","aspect_symbol","Description","Closeness"])
    return pd.DataFrame(results)


def compute_composite_bodies(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    """Near-midpoint composite chart bodies from two natal DataFrames."""
    from app.core.constants import degree_to_sign

    bodies_a = df_a[~df_a["Body"].str.contains("House Cusp")].set_index("Body")
    bodies_b = df_b[~df_b["Body"].str.contains("House Cusp")].set_index("Body")
    common = sorted(set(bodies_a.index) & set(bodies_b.index))

    results = []
    for body in common:
        lon_a = float(bodies_a.loc[body, "Longitude (°)"])
        lon_b = float(bodies_b.loc[body, "Longitude (°)"])
        diff = (lon_b - lon_a) % 360
        mid = (lon_a + diff / 2) % 360 if diff <= 180 else (lon_a - (360 - diff) / 2) % 360

        row = bodies_a.loc[body]
        results.append({
            "Body": body,
            "Longitude (°)": mid,
            "Symbol": row.get("Symbol", body[0]) if not isinstance(row.get("Symbol"), float) else body[0],
            "Color": row.get("Color", "#888888") if not isinstance(row.get("Color"), float) else "#888888",
            "Speed (°/day)": 0.0,
            "Sign": degree_to_sign(mid),
            "House": "",
            "Motion": "",
        })

    return pd.DataFrame(results)


def synastry_score(cross_aspects: pd.DataFrame) -> dict:
    """Overall synastry compatibility score and breakdown."""
    if cross_aspects.empty:
        return {"overall": 50.0, "harmony": 0.0, "tension": 0.0, "conjunction": 0.0, "total_aspects": 0, "summary": "No significant cross-aspects found."}

    HARMONIOUS = {"Trine", "Sextile", "Semi-sextile", "Quintile", "Bi-Quintile", "Novile", "Bi-Novile", "Quadri-Novile", "Decile", "Tri-Decile"}
    TENSE = {"Square", "Opposition", "Quincunx", "Semi-square", "Sesquisquare", "Septile", "Biseptile", "Triseptile"}

    harm = float(cross_aspects[cross_aspects["Aspect"].isin(HARMONIOUS)]["Closeness"].sum())
    tens = float(cross_aspects[cross_aspects["Aspect"].isin(TENSE)]["Closeness"].sum())
    conj = float(cross_aspects[cross_aspects["Aspect"] == "Conjunction"]["Closeness"].sum())
    total = harm + tens + conj

    score = round(min(100.0, (harm + 0.5 * conj) / max(total, 0.01) * 100), 1)

    if score >= 75:
        summary = "Strong harmony — these charts resonate with deep mutual support."
    elif score >= 55:
        summary = "Good compatibility with some dynamic tension that drives growth."
    elif score >= 40:
        summary = "Balanced mix of attraction and challenge."
    else:
        summary = "Strong dynamic tension — intense connection requiring conscious work."

    return {
        "overall": score,
        "harmony": round(harm, 2),
        "tension": round(tens, 2),
        "conjunction": round(conj, 2),
        "total_aspects": int(len(cross_aspects)),
        "summary": summary,
    }
