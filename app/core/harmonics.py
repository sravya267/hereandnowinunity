"""Rank Cochrane-style harmonic families by total resonance ("hum")
in a chart's aspects table.
"""
from __future__ import annotations

import math

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

# ── Natal definitions (H1-H32) ────────────────────────────────────────────────
_NATAL: dict[int, str] = {
    1:  "The complete cycle — total union of two planetary forces into one undivided expression. Represents wholeness, identity, and self-integration in the natal chart.",
    2:  "The axis of opposition — two forces at maximum separation, creating awareness through contrast. In the natal chart this marks where the person must integrate polarities to achieve balance.",
    3:  "The triangle of ease — energy flows freely between planets, producing natural talent, creative grace, and harmonious resonance. Natal trines show gifts that come without effort.",
    4:  "The cross of manifestation — dynamic tension between four points that generates effort, ambition, and the will to build. Natal squares drive achievement through persistent challenge.",
    5:  "The pentagram of creativity — Cochrane's signature of genius; distinctive style, inspired talent, and unique personal expression. Natal quintiles mark the creative fingerprint of the soul.",
    6:  "The hexagram of opportunity — cooperative energy that rewards conscious effort with productive connection and mental agility. Natal sextiles show talents developed through practice.",
    7:  "The heptagon of fate — irrational, spiritual vibration beyond rational control; karmic threads, prophetic inspiration, and soul destiny. Natal septiles reveal fated themes in the life.",
    8:  "The octagon of refinement — persistent minor friction that demands precision, discipline, and incremental mastery. Natal octiles show where the person is called to perfect a craft.",
    9:  "The nonagon of completion — spiritual fulfilment and idealistic wholeness; the soul approaching inner integration. Natal noviles reveal the highest spiritual aspirations.",
    10: "The decagon of skill — subtle creative refinement that mirrors the quintile's mastery through precise, articulate expression. Natal deciles show nuanced practical artistry.",
    11: "The undecagon of the transcendent — eccentric, anomalous patterns outside conventional frameworks; visionary or otherworldly quality. Natal undeciles mark the unconventional genius.",
    12: "The dodecagon of adjustment — subtle re-orientation between energies that do not naturally align; growth through ongoing adaptation. Natal duodeciles show flexibility and sensitivity.",
    13: "The 13th harmonic of community — consciousness of the collective and the role of the individual within it. In the natal chart this marks a drive toward belonging and group participation.",
    14: "The 14th harmonic (2×7) blends polarity with fate — an awareness of karmic opposites and the need to integrate opposing destinies. Natal H14 marks fated awareness and soul contrasts.",
    15: "The 15th harmonic (3×5) merges creative ease with genius — talent flows freely and finds unique expression. In the natal chart H15 indicates healing gifts or creative therapeutic ability.",
    16: "The 16th harmonic (4²) intensifies the square's drive into mastery and excellence — the call to build something of lasting value. Natal H16 marks the architect, the master builder.",
    17: "The 17th harmonic — Cochrane's 'theatre harmonic'; drama, empathy, storytelling, and the ability to inhabit other perspectives. Natal H17 marks actors, writers, healers, and empaths.",
    18: "The 18th harmonic (2×9) blends polarity with spiritual completion — awareness through opposites leads to integration. Natal H18 marks a deep spiritual sensitivity and philosophical nature.",
    19: "The 19th harmonic — charisma, confidence, and pioneering presence. An irreducible prime vibration expressing the self with bold individuality. Natal H19 marks magnetic leadership.",
    20: "The 20th harmonic (4×5) grounds creative genius into practical application — the builder who is also an artist. Natal H20 marks the ability to manifest inspired ideas into concrete form.",
    21: "The 21th harmonic (3×7) merges ease with fate — inspiration flows naturally, guided by a higher purpose. Natal H21 marks the inspired teacher, visionary, or spiritual guide.",
    22: "The 22nd harmonic (2×11) combines polarity with transcendence — a visionary tension between opposites that generates eccentric wisdom. Natal H22 marks the unconventional reformer.",
    23: "The 23rd harmonic — an irreducible prime of determination, resilience, and drive through adversity. Natal H23 marks the person who persists and transforms through challenge.",
    24: "The 24th harmonic (2³×3) multiplies refined discipline into harmonic precision — detailed mastery with systematic grace. Natal H24 marks the skilled craftsperson and methodical thinker.",
    25: "The 25th harmonic (5²) amplifies quintile creativity into heightened genius — the soul's deepest creative signature magnified. Natal H25 marks extraordinary originality and artistic power.",
    26: "The 26th harmonic (2×13) combines community consciousness with polarity — awareness of the collective through contrasting perspectives. Natal H26 marks the social bridge-builder.",
    27: "The 27th harmonic (3³) triples the trine's ease into profound spiritual grace — deep idealism and inner wisdom flowing naturally. Natal H27 marks the spiritual teacher or mystic sage.",
    28: "The 28th harmonic (4×7) multiplies fate's tension with the drive to manifest — karmic obligations that demand concrete action. Natal H28 marks the person with a fated mission to build.",
    29: "The 29th harmonic — an irreducible prime of philosophical wisdom and purposeful insight. Natal H29 marks the thinker, the seeker, and the one called to understand life's deeper meaning.",
    30: "The 30th harmonic (2×3×5) harmonises polarity, ease, and genius in a richly blended vibration. Natal H30 marks the versatile creative who integrates many talents into a unified vision.",
    31: "The 31st harmonic — an irreducible prime of independent vision and pioneering leadership. Natal H31 marks the original thinker who opens new paths and inspires others through innovation.",
    32: "The 32nd harmonic (2⁵) concentrates refined precision into amplified power — disciplined mastery at a very high octave. Natal H32 marks exceptional technical skill and focused willpower.",
}

# ── Transit definitions (H1-H32) ─────────────────────────────────────────────
_TRANSIT: dict[int, str] = {
    1:  "When a transiting planet conjuncts a natal planet it activates complete union — the natal planet's themes are fully and intensely awakened. H1 transits mark moments of peak identity, crisis, or renewal.",
    2:  "When a transiting planet opposes a natal point, it brings awareness through contrast — an external challenge illuminates an inner polarity. H2 transits are moments of confrontation and necessary balance.",
    3:  "When a transiting planet trines a natal point, energy flows easily — the natal theme is supported and naturally expressed. H3 transits bring grace, opportunity, and gifts that arrive without struggle.",
    4:  "When a transiting planet squares a natal point, constructive tension is activated — the natal theme is pressured to produce results. H4 transits bring challenges that ultimately forge strength.",
    5:  "When a transiting planet forms a quintile with a natal point, creative genius is awakened — a window of inspired expression opens. H5 transits are peak creative periods and breakthrough moments.",
    6:  "When a transiting planet sextiles a natal point, cooperative opportunity arises — the natal theme is supported by helpful circumstances. H6 transits bring favourable conditions that reward effort.",
    7:  "When a transiting planet forms a septile to a natal point, fated events are triggered — synchronicities, spiritual awakenings, and karmic encounters occur. H7 transits mark turning points of destiny.",
    8:  "When a transiting planet forms an octile to a natal point, a refining pressure is applied — precision and discipline are called for. H8 transits demand focus, attention to detail, and patient mastery.",
    9:  "When a transiting planet forms a novile to a natal point, a moment of spiritual completion arrives — idealism is activated and the soul feels its higher purpose. H9 transits bring transcendent clarity.",
    10: "When a transiting planet forms a decile to a natal point, subtle creative skill is activated — artistry and precision come into alignment. H10 transits bring moments of inspired craftsmanship.",
    11: "When a transiting planet forms an undecile to a natal point, an eccentric or visionary impulse is triggered — the unexpected and transcendent intrude. H11 transits bring sudden insight or revelation.",
    12: "When a transiting planet forms a duodecile to a natal point, a gentle adjustment is activated — the chart area needs subtle re-calibration. H12 transits bring sensitivity, adaptability, and quiet shifts.",
    13: "When a transiting planet activates H13 in the natal chart, community themes come to the fore — collective belonging, group dynamics, and the person's role within society become salient.",
    14: "When H14 (polarity-of-fate) is triggered by transit, karmic opposites are illuminated — fated awareness rises and the person encounters the other side of a soul lesson they are integrating.",
    15: "When H15 (creative-healing) is activated by transit, healing gifts come online — a period of therapeutic creativity, artistic breakthroughs, or the resolution of old creative blocks.",
    16: "When H16 (mastery) is activated by transit, a call to excellence arrives — building projects, career achievements, and the drive to create lasting structures intensify.",
    17: "When H17 (theatre-empathy) is activated by transit, dramatic or empathic experiences are highlighted — performances, emotional encounters, or the ability to inhabit other perspectives peaks.",
    18: "When H18 (spiritual-polarity) is activated by transit, the person encounters a spiritually significant opposite — a philosophical challenge or spiritual contrast that deeps integration.",
    19: "When H19 (charisma) is activated by transit, magnetic confidence surfaces — a period of bold self-expression, leadership presence, and the ability to attract and inspire others.",
    20: "When H20 (practical-genius) is activated by transit, inspired ideas can be concretely realised — a favourable window for manifesting creative projects into tangible outcomes.",
    21: "When H21 (inspired-ease) is activated by transit, spiritual guidance flows naturally — a period of inspired teaching, visionary creativity, or alignment with a higher purpose.",
    22: "When H22 (visionary-tension) is activated by transit, unconventional or reforming impulses are triggered — the person is called to challenge convention and express an eccentric wisdom.",
    23: "When H23 (resilience) is activated by transit, the person is tested and tempered — adversity becomes a forge; perseverance and determination are called out in full measure.",
    24: "When H24 (precise-harmony) is activated by transit, a period of systematic refinement arrives — the person can achieve exceptional detail, methodical precision, and disciplined grace.",
    25: "When H25 (amplified-genius) is activated by transit, extraordinary creative power surges — a peak of originality, artistic brilliance, or breakthrough inspiration.",
    26: "When H26 (community-polarity) is activated by transit, social awareness intensifies — the person bridges opposing community perspectives or becomes a connector within a larger group.",
    27: "When H27 (spiritual-grace) is activated by transit, wisdom flows freely — a period of deep inner calm, spiritual teaching, or the natural expression of hard-won wisdom.",
    28: "When H28 (fated-action) is activated by transit, a karmic obligation becomes urgent — the person is called to take decisive action on a fated matter that can no longer be deferred.",
    29: "When H29 (philosophical-wisdom) is activated by transit, the person is drawn into deep thinking — a period of profound insight, purpose-driven decisions, or philosophical breakthroughs.",
    30: "When H30 (creative-synthesis) is activated by transit, diverse talents integrate into a unified creative vision — the person can bring multiple strands together with surprising versatility.",
    31: "When H31 (pioneering-vision) is activated by transit, the person feels called to blaze a new trail — original thinking, independent leadership, and the courage to innovate come to the fore.",
    32: "When H32 (concentrated-power) is activated by transit, focused willpower is amplified — the person can achieve extraordinary precision and discipline, directing intense effort toward a goal.",
}

# ── Synastry definitions (H1-H32) ─────────────────────────────────────────────
_SYNASTRY: dict[int, str] = {
    1:  "When two people's planets align at H1 (conjunction), they experience a sense of complete merger — a powerful, often overwhelming resonance of shared identity and purpose.",
    2:  "When two people's planets align at H2 (opposition), they awaken each other's polarities — each person mirrors the other's shadow, creating a magnetic attraction built on contrast and balance.",
    3:  "When two people share H3 (trine) resonance, energy flows easily between them — natural harmony, mutual support, and an effortless ability to enjoy each other's company and gifts.",
    4:  "When two people share H4 (square) resonance, dynamic tension sparks between them — they challenge and motivate each other, creating a productive friction that drives mutual growth.",
    5:  "When two people share H5 (quintile) resonance, they inspire each other's creative genius — a creative partnership of rare quality where each brings out the other's most original expression.",
    6:  "When two people share H6 (sextile) resonance, they open doors of opportunity for one another — a helpful, stimulating connection where cooperative effort produces practical rewards.",
    7:  "When two people share H7 (septile) resonance, they feel fated to meet — a karmic bond, spiritual significance, and a sense that the relationship serves a higher, destined purpose.",
    8:  "When two people share H8 (octile) resonance, they refine and sharpen each other — a subtle but persistent friction that calls both parties to greater precision, discipline, and mastery.",
    9:  "When two people share H9 (novile) resonance, they bring out each other's highest idealism — a spiritually charged bond where both feel called toward a shared vision of wholeness and beauty.",
    10: "When two people share H10 (decile) resonance, they appreciate and develop each other's practical artistry — a connection of skilled mutual refinement and creative craftsmanship.",
    11: "When two people share H11 (undecile) resonance, they catalyse each other's eccentric brilliance — a uniquely unconventional bond where neither person can be ordinary in the other's presence.",
    12: "When two people share H12 (duodecile) resonance, they gently recalibrate each other — a soft, sensitive connection requiring ongoing adjustment and mutual attentiveness to subtle needs.",
    13: "When two people share H13 resonance, they feel a bond of communal kinship — a connection rooted in shared belonging, collective ideals, or a sense of being part of the same tribe.",
    14: "When two people share H14 resonance, they encounter each other as karmic mirrors — an intense awareness of fated contrasts that feel both inevitable and transformative.",
    15: "When two people share H15 resonance, they heal each other through creative expression — a therapeutic bond where artistic collaboration or creative play facilitates deep mutual healing.",
    16: "When two people share H16 resonance, they build together with masterful ambition — a partnership of excellence where both are driven to create something of outstanding quality and endurance.",
    17: "When two people share H17 resonance, they perform for and with each other — deep empathy, dramatic resonance, and the ability to fully inhabit each other's inner world and story.",
    18: "When two people share H18 resonance, they awaken each other's spiritual depths — an encounter with the sacred through relationship, where polarity becomes a path to higher integration.",
    19: "When two people share H19 resonance, they boost each other's confidence and charisma — a dynamic energising bond where each becomes more powerfully themselves in the other's presence.",
    20: "When two people share H20 resonance, they help each other materialise inspired visions — a practical creative partnership that turns original ideas into concrete, real-world achievements.",
    21: "When two people share H21 resonance, they inspire each other with a sense of shared spiritual purpose — a flow of mutual inspiration, teaching, and guidance toward a common higher vision.",
    22: "When two people share H22 resonance, they challenge each other's orthodoxies — an unconventional, thought-provoking bond that liberates both from limiting assumptions.",
    23: "When two people share H23 resonance, they strengthen each other's resilience — a bond forged through shared challenges where both emerge tougher, more determined, and more capable.",
    24: "When two people share H24 resonance, they refine each other's methods — a disciplined, precise partnership where systematic collaboration produces exceptional, detailed work.",
    25: "When two people share H25 resonance, they amplify each other's creative genius — an artistically explosive connection where both are inspired to their highest creative potential.",
    26: "When two people share H26 resonance, they connect across contrasting social worlds — a bridge-building bond that creates understanding between different communities or perspectives.",
    27: "When two people share H27 resonance, they draw out each other's deepest wisdom — a spiritually profound bond of natural grace where both feel seen in their most integrated self.",
    28: "When two people share H28 resonance, they activate each other's sense of fated mission — a bond that carries weight and purpose, driving both to act on karmic obligations together.",
    29: "When two people share H29 resonance, they inspire each other's philosophical depth — a meeting of minds that generates profound insight, mutual wisdom, and a shared pursuit of meaning.",
    30: "When two people share H30 resonance, they harmonise each other's diverse talents — a richly creative bond where synthesis, versatility, and multiple forms of expression all thrive together.",
    31: "When two people share H31 resonance, they pioneer together — a bond of independent vision that encourages both to break new ground and lead from a place of original authentic truth.",
    32: "When two people share H32 resonance, they focus and amplify each other's power — a highly concentrated bond of mutual discipline and excellence that generates remarkable willpower.",
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
    """Return sorted list of unique prime factors of n (no repetition)."""
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


def _factorization(n: int) -> str:
    """Full prime factorization with repetition, e.g. 12 → '2×2×3'.

    Primes return their own value; 1 returns '1'.
    """
    if n <= 1:
        return str(n)
    factors: list[int] = []
    d, m = 2, n
    while d * d <= m:
        while m % d == 0:
            factors.append(d)
            m //= d
        d += 1
    if m > 1:
        factors.append(m)
    return "×".join(str(f) for f in factors)


def _factor_names(h: int) -> str:
    """Return a readable string of unique prime factor names, e.g. 'H2, H3, H5'."""
    return ", ".join(f"H{p}" for p in _prime_factors(h))


def _natal_definition(h: int) -> str:
    if h in _NATAL:
        return _NATAL[h]
    if _is_prime(h):
        return (
            f"Prime harmonic resonating at {360 / h:.4f}° — an irreducible natal vibration "
            f"with a unique, undivided frequency. Marks a specialised quality of character "
            f"that operates independently of all other harmonic families."
        )
    factors = _prime_factors(h)
    factor_str = _factor_names(h)
    aspect_deg = round(360 / h, 4)
    return (
        f"Composite natal harmonic ({factor_str}) resonating at {aspect_deg}°. "
        f"The natal chart qualities of its prime factors ({', '.join(str(p) for p in factors)}) "
        f"blend and mutually amplify one another, producing a specialised signature that "
        f"combines the themes of each constituent prime harmonic."
    )


def _transit_definition(h: int) -> str:
    if h in _TRANSIT:
        return _TRANSIT[h]
    if _is_prime(h):
        return (
            f"When a transiting planet activates this prime H{h} point in the natal chart "
            f"({360 / h:.4f}°), a specialised and irreducible theme is triggered — an area "
            f"of unique personal significance that cannot be reduced to any other harmonic family. "
            f"These transits can feel unusual or distinctly personal."
        )
    factors = _prime_factors(h)
    factor_str = _factor_names(h)
    aspect_deg = round(360 / h, 4)
    return (
        f"When a transiting planet activates this composite H{h} point ({aspect_deg}°) in the natal chart, "
        f"it simultaneously stimulates the blended themes of {factor_str}. "
        f"The transit triggers a convergence of those prime harmonic qualities, "
        f"activating their combined influence in the area of the natal chart contacted."
    )


def _synastry_definition(h: int) -> str:
    if h in _SYNASTRY:
        return _SYNASTRY[h]
    if _is_prime(h):
        return (
            f"When two people's planets align at H{h} ({360 / h:.4f}°), they activate a "
            f"unique, irreducible resonance between them — a rare and specialised connection "
            f"that stimulates a theme found in no other harmonic family. Such bonds are "
            f"distinctive and often feel singular or hard to articulate."
        )
    factors = _prime_factors(h)
    factor_str = _factor_names(h)
    aspect_deg = round(360 / h, 4)
    return (
        f"When two people's planets align at this composite H{h} ({aspect_deg}°), "
        f"they activate a blended resonance combining the interpersonal themes of {factor_str}. "
        f"The relationship simultaneously carries the qualities of each prime harmonic, "
        f"creating a multi-layered dynamic that weaves those harmonic themes together."
    )


def _definition(h: int) -> str:
    """Legacy single definition — returns natal definition."""
    return _natal_definition(h)


_MAX_HARMONIC = 360
_RANGE = range(1, _MAX_HARMONIC + 1)

VIBRATIONAL_HARMONICS: pd.DataFrame = pd.DataFrame({
    "harmonic":            list(_RANGE),
    "aspect_degree":       [round(360 / h, 6) for h in _RANGE],
    "name":                [HARMONIC_NAMES.get(h, f"H{h}") for h in _RANGE],
    "prime":               [_is_prime(h) for h in _RANGE],
    "prime_factorization": [_factorization(h) for h in _RANGE],
    "natal_definition":    [_natal_definition(h) for h in _RANGE],
    "transit_definition":  [_transit_definition(h) for h in _RANGE],
    "synastry_definition": [_synastry_definition(h) for h in _RANGE],
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
