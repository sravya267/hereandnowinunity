"""FastAPI route handlers for the chart API."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, Response

from app.api.schemas import BirthMomentResponse, ChartRequest, ChartResponse
from app.core.chart import compute_chart
from app.core.geocoding import LocationNotFound
from app.core.notify import notify_new_chart
from app.core.visualization import generate_wordclouds, generate_zodiac_chart

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.post("/chart/wheel", response_class=HTMLResponse)
def chart_wheel(req: ChartRequest) -> HTMLResponse:
    """Render the zodiac wheel as standalone HTML."""
    try:
        chart = compute_chart(
            birth_datetime=req.birth_datetime,
            location_name=req.location,
            zodiac_system=req.zodiac_system,
            house_system=req.house_system,
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
