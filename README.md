# Astro Chart

Natal chart calculation and visualization service. Computes planetary positions, house cusps, and aspects using the Swiss Ephemeris, renders an interactive zodiac wheel with Plotly, and exposes everything through a FastAPI service ready for Google Cloud Run.

## What it does

Given a birth date, time, and place, the service returns:

- Planetary longitudes, declinations, speeds, and signs (tropical or sidereal)
- House cusps plus Ascendant, MC, Descendant, and IC
- Aspects between bodies (conjunctions, oppositions, trines, squares, quintiles, etc.) with orbs and closeness scores
- An interactive Plotly zodiac chart (HTML)
- Strength and stress word clouds derived from planet–sign–house trait mappings

## Quick start

```bash
# 1. Install dependencies (Python 3.11+)
pip install -r requirements.txt

# 2. Download Swiss Ephemeris data files (one-time, ~28 MB)
python scripts/download_ephemeris.py

# 3. Run the API
uvicorn app.main:app --reload
```

Then open `http://localhost:8000/docs` for the interactive API documentation.

## API

| Endpoint | Description |
|----------|-------------|
| `POST /chart` | Full chart: positions, houses, aspects as JSON |
| `POST /chart/wheel` | Interactive zodiac wheel as HTML |
| `POST /chart/wordcloud` | Strengths and stress traits as PNG |
| `GET /health` | Health check |

Example request:

```bash
curl -X POST http://localhost:8000/chart \
  -H "Content-Type: application/json" \
  -d '{
    "birth_datetime": "1969-06-14T04:40:00",
    "location": "Mannheim",
    "zodiac_system": "Tropical"
  }'
```

## Deployment to Google Cloud Run

```bash
# Build and deploy
gcloud run deploy astro-chart \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

The `Dockerfile` bundles the ephemeris files into the image, so there is no cold-start download penalty and no external storage dependency at runtime.

## Project structure

```
astro-chart/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Settings (paths, env vars)
│   ├── core/
│   │   ├── constants.py     # Zodiac, planets, aspects tables
│   │   ├── ephemeris.py     # Swiss Ephemeris calculations
│   │   ├── geocoding.py     # Location → lat/lon/timezone
│   │   ├── aspects.py       # Aspect detection
│   │   ├── chart.py         # Full chart assembly
│   │   └── visualization.py # Plotly wheel, word clouds
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Pydantic request/response models
│   └── data/
│       └── ai_personalities.csv  # Trait mappings
├── ephe/                    # Swiss Ephemeris .se1 files (gitignored)
├── scripts/
│   └── download_ephemeris.py
├── tests/
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

## License

The Swiss Ephemeris is dual-licensed (AGPL-3.0 or commercial). This project follows AGPL-3.0 in line with `pyswisseph`.
