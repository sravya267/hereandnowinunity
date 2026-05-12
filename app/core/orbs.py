"""Shared orb-formula logic for aspects and harmonic matrix.

A single source of truth so traditional aspects (``aspects.py``) and the
full H1-H360 harmonic matrix (``harmonic_matrix.py``) use the same rule.

Three formulas are supported:

    "sqrt"   orb(h) = base_orb / sqrt(h)    — generous, default
    "linear" orb(h) = base_orb / h          — strict (Cochrane-style)
    "fixed"  orb(h) = base_orb              — same orb for every harmonic

``base_orb`` is the orb at H1 in degrees of natal-chart separation.
"""
from __future__ import annotations

from typing import Literal

import numpy as np

OrbFormula = Literal["sqrt", "linear", "fixed"]

DEFAULT_BASE_ORB: float = 8.0
DEFAULT_FORMULA: OrbFormula = "sqrt"


def orb_limit(
    h: int | np.ndarray,
    base_orb: float = DEFAULT_BASE_ORB,
    formula: OrbFormula = DEFAULT_FORMULA,
) -> float | np.ndarray:
    """Return the per-harmonic orb limit in natal-chart degrees.

    Works elementwise on numpy arrays so it can be applied to all 360
    harmonics at once.
    """
    if formula == "sqrt":
        return base_orb / np.sqrt(h)
    if formula == "linear":
        return base_orb / h
    if formula == "fixed":
        if isinstance(h, np.ndarray):
            return np.full_like(h, base_orb, dtype=float)
        return float(base_orb)
    raise ValueError(f"Unknown orb formula: {formula!r}")
