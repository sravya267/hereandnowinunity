# syntax=docker/dockerfile:1.6
#
# Multi-stage build for Cloud Run.
#   - stage 1 (ephe):    downloads Swiss Ephemeris data files
#   - stage 2 (builder): installs Python deps into a virtualenv
#   - stage 3 (runtime): slim final image, copies venv + ephe + app code
#
# Running locally:
#   docker build -t astro-chart .
#   docker run -p 8080:8080 astro-chart

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS ephe

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY scripts/download_ephemeris.py scripts/download_ephemeris.py
RUN python scripts/download_ephemeris.py

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# System libs needed by matplotlib/wordcloud at runtime (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libxext6 libsm6 libxrender1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EPHE_PATH=/app/ephe

COPY --from=builder /opt/venv /opt/venv
COPY --from=ephe /build/ephe /app/ephe
COPY app/ /app/app/

RUN chown -R appuser:appuser /app
USER appuser

# Cloud Run sets PORT; default 8080 for local runs
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
