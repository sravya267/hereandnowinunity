"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload

Cloud Run will set ``PORT`` and run ``app.main:app`` via the Dockerfile.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Astro Chart",
    description="Natal chart calculation and visualization API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")
