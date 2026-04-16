"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload

Cloud Run will set ``PORT`` and run ``app.main:app`` via the Dockerfile.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

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


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "astro-chart",
        "docs": "/docs",
        "health": "/health",
    }
