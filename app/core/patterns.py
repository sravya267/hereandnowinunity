"""Detect named multi-planet aspect patterns in a chart.

Patterns detected: Grand Trine, T-Square, Yod (Finger of God),
Grand Cross, Kite, Mystic Rectangle.  Each result carries a
closeness score (0–1) so callers can sort/filter by tightness.
"""
from __future__ import annotations

from itertools import combinations

import pandas as pd

_SKIP_FRAGMENTS = ("House Cusp",)


def detect_patterns(aspects_df: pd.DataFrame) -> list[dict]:
    """Return a list of pattern dicts sorted by descending score.

    Parameters
    ----------
    aspects_df
        Output of :func:`app.core.aspects.calculate_aspects`.
        Must have columns Body1, Body2, Aspect, Closeness.
    """
    if aspects_df.empty:
        return []

    # Two-way lookup: (b1, b2) -> Series row
    asp_map: dict[tuple[str, str], pd.Series] = {}
    for _, row in aspects_df.iterrows():
        asp_map[(row["Body1"], row["Body2"])] = row
        asp_map[(row["Body2"], row["Body1"])] = row

    def get(b1: str, b2: str) -> pd.Series | None:
        return asp_map.get((b1, b2))

    def has(b1: str, b2: str, *types: str) -> bool:
        a = get(b1, b2)
        return a is not None and a["Aspect"] in types

    def sc(b1: str, b2: str) -> float:
        a = get(b1, b2)
        return float(a["Closeness"]) if a is not None else 0.0

    # Bodies that appear in at least one aspect (skip house cusps)
    bodies = sorted({
        b
        for b in pd.concat([aspects_df["Body1"], aspects_df["Body2"]])
        if not any(s in b for s in _SKIP_FRAGMENTS)
    })

    results: list[dict] = []

    # ── Grand Trine ──────────────────────────────────────────────────────────
    for a, b, c in combinations(bodies, 3):
        if has(a, b, "Trine") and has(b, c, "Trine") and has(a, c, "Trine"):
            score = (sc(a, b) + sc(b, c) + sc(a, c)) / 3
            results.append({
                "type": "Grand Trine",
                "bodies": [a, b, c],
                "score": round(score, 3),
                "description": "A flowing triangle of natural talent and ease.",
            })

    # ── T-Square ─────────────────────────────────────────────────────────────
    for a, b, c in combinations(bodies, 3):
        for opp1, opp2, apex in ((a, b, c), (a, c, b), (b, c, a)):
            if (
                has(opp1, opp2, "Opposition")
                and has(opp1, apex, "Square")
                and has(opp2, apex, "Square")
            ):
                score = (sc(opp1, opp2) + sc(opp1, apex) + sc(opp2, apex)) / 3
                results.append({
                    "type": "T-Square",
                    "bodies": [opp1, opp2, apex],
                    "apex": apex,
                    "score": round(score, 3),
                    "description": f"Tension seeking resolution through {apex}.",
                })

    # ── Yod (Finger of God) ──────────────────────────────────────────────────
    for a, b, c in combinations(bodies, 3):
        for q1, q2, apex in ((a, b, c), (a, c, b), (b, c, a)):
            if (
                has(q1, q2, "Sextile")
                and has(q1, apex, "Quincunx")
                and has(q2, apex, "Quincunx")
            ):
                score = (sc(q1, q2) + sc(q1, apex) + sc(q2, apex)) / 3
                results.append({
                    "type": "Yod",
                    "bodies": [q1, q2, apex],
                    "apex": apex,
                    "score": round(score, 3),
                    "description": f"Karmic mission — Finger of God pointing to {apex}.",
                })

    # ── Grand Cross ──────────────────────────────────────────────────────────
    # 4 planets at ~90° intervals: 2 oppositions + 4 squares.
    _gc_seen: set[frozenset] = set()
    for a, b, c, d in combinations(bodies, 4):
        for p1, p2, p3, p4 in ((a, b, c, d), (a, c, b, d), (a, d, b, c)):
            if (
                has(p1, p3, "Opposition") and has(p2, p4, "Opposition")
                and has(p1, p2, "Square") and has(p2, p3, "Square")
                and has(p3, p4, "Square") and has(p4, p1, "Square")
            ):
                key = frozenset((a, b, c, d))
                if key not in _gc_seen:
                    _gc_seen.add(key)
                    score = (
                        sc(p1, p3) + sc(p2, p4)
                        + sc(p1, p2) + sc(p2, p3) + sc(p3, p4) + sc(p4, p1)
                    ) / 6
                    results.append({
                        "type": "Grand Cross",
                        "bodies": [p1, p2, p3, p4],
                        "score": round(score, 3),
                        "description": "Four-way tension demanding balance and integration.",
                    })
                break

    # ── Kite ─────────────────────────────────────────────────────────────────
    # Grand trine + extra planet opposing one vertex and sextiling the other two.
    trine_sets = [
        (a, b, c)
        for a, b, c in combinations(bodies, 3)
        if has(a, b, "Trine") and has(b, c, "Trine") and has(a, c, "Trine")
    ]
    _kt_seen: set[frozenset] = set()
    for a, b, c in trine_sets:
        for apex, s1, s2 in ((a, b, c), (b, a, c), (c, a, b)):
            for d in bodies:
                if d in (a, b, c):
                    continue
                if (
                    has(d, apex, "Opposition")
                    and has(d, s1, "Sextile")
                    and has(d, s2, "Sextile")
                ):
                    key = frozenset((a, b, c, d))
                    if key not in _kt_seen:
                        _kt_seen.add(key)
                        score = (
                            sc(a, b) + sc(b, c) + sc(a, c)
                            + sc(d, apex) + sc(d, s1) + sc(d, s2)
                        ) / 6
                        results.append({
                            "type": "Kite",
                            "bodies": [a, b, c, d],
                            "apex": apex,
                            "score": round(score, 3),
                            "description": (
                                f"Grand Trine energised by {d} opposing {apex}."
                            ),
                        })

    # ── Mystic Rectangle ─────────────────────────────────────────────────────
    # 4 planets: 2 oppositions + 2 trines + 2 sextiles.
    _mr_seen: set[frozenset] = set()
    for a, b, c, d in combinations(bodies, 4):
        for p1, p2, p3, p4 in ((a, b, c, d), (a, c, b, d), (a, d, b, c)):
            if (
                has(p1, p3, "Opposition") and has(p2, p4, "Opposition")
                and has(p1, p2, "Trine") and has(p3, p4, "Trine")
                and has(p1, p4, "Sextile") and has(p2, p3, "Sextile")
            ):
                key = frozenset((a, b, c, d))
                if key not in _mr_seen:
                    _mr_seen.add(key)
                    score = (
                        sc(p1, p3) + sc(p2, p4)
                        + sc(p1, p2) + sc(p3, p4)
                        + sc(p1, p4) + sc(p2, p3)
                    ) / 6
                    results.append({
                        "type": "Mystic Rectangle",
                        "bodies": [p1, p2, p3, p4],
                        "score": round(score, 3),
                        "description": "Harmonious rectangle bridging two oppositions.",
                    })
                break

    # Sort by score descending, deduplicate by (type, bodies-frozenset)
    results.sort(key=lambda x: -x["score"])
    seen: set[tuple] = set()
    unique: list[dict] = []
    for r in results:
        key2 = (r["type"], frozenset(r["bodies"]))
        if key2 not in seen:
            seen.add(key2)
            unique.append(r)
    return unique
