"""FastAPI route handlers for the chart API."""
from __future__ import annotations

import logging
import smtplib

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, Response

from app.api.schemas import BirthMomentResponse, ChartRequest, ChartResponse, HarmonicsRequest, SynastryRequest, SynastryHarmonicsRequest, SynastryResponse
from app.core.chart import compute_chart
from app.core.geocoding import LocationNotFound
from app.core.notify import notify_new_chart
from app.core.visualization import generate_wordclouds, generate_zodiac_chart

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/notify/test")
def notify_test() -> dict:
    """Send a test notification and return a detailed status report."""
    from app.config import settings

    report: dict = {
        "provider": settings.NOTIFY_PROVIDER or "(not set — notifications disabled)",
        "owner_email": settings.OWNER_EMAIL,
        "gmail_user": settings.GMAIL_USER,
        "gmail_app_password_set": bool(settings.GMAIL_APP_PASSWORD),
        "resend_api_key_set": bool(settings.RESEND_API_KEY),
        "notify_webhook_url_set": bool(settings.NOTIFY_WEBHOOK_URL),
        "result": None,
        "error": None,
    }

    if not settings.NOTIFY_PROVIDER:
        report["result"] = "skipped — NOTIFY_PROVIDER is empty"
        return report

    if settings.NOTIFY_PROVIDER == "gmail":
        if not (settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD and settings.OWNER_EMAIL):
            report["result"] = "skipped — missing GMAIL_USER, GMAIL_APP_PASSWORD, or OWNER_EMAIL"
            return report
        try:
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["From"] = settings.GMAIL_USER
            msg["To"] = settings.OWNER_EMAIL
            msg["Subject"] = "Test — astro chart notification"
            msg.set_content("This is a test notification from hereandnowinunity.")
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
                smtp.send_message(msg)
            report["result"] = "sent OK"
        except smtplib.SMTPAuthenticationError as exc:
            report["result"] = "failed"
            report["error"] = f"Authentication error — App Password likely invalid or revoked: {exc}"
        except Exception as exc:  # noqa: BLE001
            report["result"] = "failed"
            report["error"] = str(exc)
        return report

    # For other providers just fire the real function and report attempt
    try:
        notify_new_chart("test", "test", "Tropical", "P")
        report["result"] = "called — check logs for errors"
    except Exception as exc:  # noqa: BLE001
        report["result"] = "failed"
        report["error"] = str(exc)
    return report

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to JSON-safe records (NaN → None, numpy → native)."""
    return df.replace({np.nan: None}).to_dict(orient="records")


@router.get("/health")
def health() -> dict:
    """Liveness probe for Cloud Run."""
    from pathlib import Path

    import swisseph as swe

    from app.config import settings

    swe.set_ephe_path(settings.EPHE_PATH)
    ephe = Path(settings.EPHE_PATH)
    files = sorted(f.name for f in ephe.glob("*")) if ephe.is_dir() else []
    try:
        pos, _ = swe.calc_ut(2451545.0, swe.SUN, 0)
        calc_ok = True
        calc_err = None
    except Exception as exc:
        calc_ok = False
        calc_err = str(exc)
    return {
        "status": "ok",
        "ephe_path": settings.EPHE_PATH,
        "ephe_exists": ephe.is_dir(),
        "ephe_files": files,
        "swe_calc_test": calc_ok,
        "swe_calc_error": calc_err,
    }


@router.post("/chart", response_model=ChartResponse)
def create_chart(req: ChartRequest, background: BackgroundTasks) -> ChartResponse:
    """Compute a full natal chart as JSON."""
    # Honeypot bot check: real users never see/fill this field.
    if req.website:
        logger.info("Bot submission rejected (honeypot tripped)")
        raise HTTPException(status_code=400, detail="Invalid submission")
    try:
        chart = compute_chart(
            birth_datetime=req.birth_datetime,
            location_name=req.location,
            zodiac_system=req.zodiac_system,
            house_system=req.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
    except LocationNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chart computation failed")
        raise HTTPException(status_code=500, detail=f"Chart computation failed: {exc}") from exc

    # Owner notification (no-ops if env vars unset)
    background.add_task(
        notify_new_chart,
        birth_datetime=req.birth_datetime.isoformat(),
        location=req.location,
        zodiac_system=req.zodiac_system,
        house_system=req.house_system,
    )

    return ChartResponse(
        birth_datetime=chart.birth_datetime,
        location=chart.location_name,
        zodiac_system=chart.zodiac_system,
        moment=BirthMomentResponse(
            latitude=chart.moment.latitude,
            longitude=chart.moment.longitude,
            timezone=chart.moment.timezone,
            julian_day_ut=chart.moment.julian_day_ut,
        ),
        bodies=_df_to_records(chart.bodies),
        aspects=_df_to_records(chart.aspects),
        ayanamsa=chart.ayanamsa,
        traits=chart.traits,
        patterns=chart.patterns,
        harmonics=chart.harmonics,
    )


@router.post("/harmonics")
def compute_harmonics_endpoint(req: HarmonicsRequest) -> dict:
    """Compute harmonic matrix resonance for a chart.

    Returns ranked harmonics (one row per harmonic) and the top long-form
    hits (one row per pair × harmonic), filtered to the requested active
    bodies and tightness threshold.
    """
    try:
        chart = compute_chart(
            birth_datetime=req.birth_datetime,
            location_name=req.location,
            zodiac_system=req.zodiac_system,
            house_system=req.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
    except LocationNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Harmonics computation failed")
        raise HTTPException(status_code=500, detail=f"Computation failed: {exc}") from exc

    from app.core.harmonic_matrix import compute_harmonic_long, rank_harmonics

    active = set(req.active_bodies)
    bodies_df = chart.bodies[chart.bodies["Body"].isin(active)].copy()

    long_df = compute_harmonic_long(
        bodies_df,
        max_harmonic=req.max_harmonic,
        base_orb=req.base_orb,
        orb_formula=req.orb_formula,
        min_tightness_pct=req.min_tightness_pct,
    )
    ranked = rank_harmonics(long_df, personal_only=req.personal_only)

    return {
        "ranked": _df_to_records(ranked),
        "hits": _df_to_records(long_df.head(200)),
    }


@router.post("/chart/wheel", response_class=HTMLResponse)
def chart_wheel(req: ChartRequest) -> HTMLResponse:
    """Render the zodiac wheel as standalone HTML."""
    try:
        chart = compute_chart(
            birth_datetime=req.birth_datetime,
            location_name=req.location,
            zodiac_system=req.zodiac_system,
            house_system=req.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
    except LocationNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    fig = generate_zodiac_chart(chart.bodies, chart.aspects, chart.zodiac_system)
    html = fig.to_html(include_plotlyjs="cdn", full_html=True, config={"responsive": True})
    return HTMLResponse(content=html)


@router.post(
    "/chart/wordcloud",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
def chart_wordcloud(req: ChartRequest) -> Response:
    """Render the strengths/stress word-cloud image as PNG."""
    try:
        chart = compute_chart(
            birth_datetime=req.birth_datetime,
            location_name=req.location,
            zodiac_system=req.zodiac_system,
            house_system=req.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
        png_bytes = generate_wordclouds(chart.bodies)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Personalities CSV not found. Ensure app/data/ai_personalities.csv exists.",
        ) from exc
    except LocationNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(content=png_bytes, media_type="image/png")


@router.post("/synastry", response_model=SynastryResponse)
def compute_synastry(req: SynastryRequest) -> SynastryResponse:
    """Compute synastry: cross-aspects, composite chart, and compatibility score."""
    try:
        chart_a = compute_chart(
            birth_datetime=req.person_a.birth_datetime,
            location_name=req.person_a.location,
            zodiac_system=req.person_a.zodiac_system,
            house_system=req.person_a.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
        chart_b = compute_chart(
            birth_datetime=req.person_b.birth_datetime,
            location_name=req.person_b.location,
            zodiac_system=req.person_b.zodiac_system,
            house_system=req.person_b.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
    except LocationNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Synastry computation failed")
        raise HTTPException(status_code=500, detail=f"Computation failed: {exc}") from exc

    from app.core.synastry import calculate_cross_aspects, compute_composite_bodies, synastry_score
    from app.core.aspects import calculate_aspects
    import numpy as _np

    cross_df = calculate_cross_aspects(chart_a.bodies, chart_b.bodies, req.base_orb, req.orb_formula)
    comp_bodies = compute_composite_bodies(chart_a.bodies, chart_b.bodies)

    # Add Rotated_Pos for composite wheel (rotate so Desc is at 0°)
    desc_row = comp_bodies[comp_bodies["Body"] == "Desc"]["Longitude (°)"]
    rot = float(desc_row.iloc[0]) if not desc_row.empty else 0.0
    comp_bodies = comp_bodies.copy()
    comp_bodies["Rotated_Pos"] = comp_bodies["Longitude (°)"] - rot
    rad = _np.deg2rad(comp_bodies["Rotated_Pos"])
    comp_bodies["rad_rot_x"] = _np.cos(rad)
    comp_bodies["rad_rot_y"] = _np.sin(rad)

    comp_aspects = calculate_aspects(comp_bodies, base_orb=req.base_orb, orb_formula=req.orb_formula)
    score = synastry_score(cross_df)

    def _chart_resp(chart):
        return ChartResponse(
            birth_datetime=chart.birth_datetime,
            location=chart.location_name,
            zodiac_system=chart.zodiac_system,
            moment=BirthMomentResponse(
                latitude=chart.moment.latitude,
                longitude=chart.moment.longitude,
                timezone=chart.moment.timezone,
                julian_day_ut=chart.moment.julian_day_ut,
            ),
            bodies=_df_to_records(chart.bodies),
            aspects=_df_to_records(chart.aspects),
            ayanamsa=chart.ayanamsa,
            traits=chart.traits,
            patterns=chart.patterns,
            harmonics=chart.harmonics,
        )

    return SynastryResponse(
        chart_a=_chart_resp(chart_a),
        chart_b=_chart_resp(chart_b),
        cross_aspects=_df_to_records(cross_df),
        composite_bodies=_df_to_records(comp_bodies),
        composite_aspects=_df_to_records(comp_aspects),
        score=score,
    )


@router.post("/synastry/harmonics")
def synastry_harmonics(req: SynastryHarmonicsRequest) -> dict:
    """Cross-chart harmonic resonance between two natal charts."""
    try:
        chart_a = compute_chart(
            birth_datetime=req.person_a.birth_datetime,
            location_name=req.person_a.location,
            zodiac_system=req.person_a.zodiac_system,
            house_system=req.person_a.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
        chart_b = compute_chart(
            birth_datetime=req.person_b.birth_datetime,
            location_name=req.person_b.location,
            zodiac_system=req.person_b.zodiac_system,
            house_system=req.person_b.house_system,
            base_orb=req.base_orb,
            orb_formula=req.orb_formula,
        )
    except LocationNotFound as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Synastry harmonics failed")
        raise HTTPException(status_code=500, detail=f"Computation failed: {exc}") from exc

    from app.core.harmonic_matrix import compute_harmonic_long, rank_harmonics

    active = set(req.active_bodies)

    # Prefix bodies so they're distinguishable, then combine
    bodies_a = chart_a.bodies[chart_a.bodies["Body"].isin(active)].copy()
    bodies_b = chart_b.bodies[chart_b.bodies["Body"].isin(active)].copy()
    bodies_a = bodies_a.copy(); bodies_a["Body"] = "A:" + bodies_a["Body"]
    bodies_b = bodies_b.copy(); bodies_b["Body"] = "B:" + bodies_b["Body"]
    combined = pd.concat([bodies_a, bodies_b], ignore_index=True)

    long_df = compute_harmonic_long(
        combined,
        max_harmonic=req.max_harmonic,
        base_orb=req.base_orb,
        orb_formula=req.orb_formula,
        min_tightness_pct=req.min_tightness_pct,
    )

    # Keep only cross-pairs (one A: and one B:)
    if not long_df.empty:
        is_cross = (
            (long_df["Body1"].str.startswith("A:") & long_df["Body2"].str.startswith("B:")) |
            (long_df["Body1"].str.startswith("B:") & long_df["Body2"].str.startswith("A:"))
        )
        long_df = long_df[is_cross].copy()
        # Strip prefixes for display
        long_df["Body1"] = long_df["Body1"].str.replace("^[AB]:", "", regex=True)
        long_df["Body2"] = long_df["Body2"].str.replace("^[AB]:", "", regex=True)

    ranked = rank_harmonics(long_df, personal_only=False)

    return {
        "ranked": _df_to_records(ranked),
        "hits": _df_to_records(long_df.head(200)),
    }
