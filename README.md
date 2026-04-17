# Astro Chart — hereandnowinunity

Natal chart calculation and visualization webapp. Computes planetary positions, house cusps, and aspects using the Swiss Ephemeris, renders an interactive zodiac wheel with Plotly, and exposes everything through a FastAPI service deployed on Google Cloud Run.

## What it does

Given a birth date, time, and place, the service returns:

- Planetary longitudes, declinations, speeds, and signs (tropical or sidereal)
- House cusps plus Ascendant, MC, Descendant, and IC
- Aspects between bodies (conjunctions, oppositions, trines, squares, quintiles, etc.) with orbs and closeness scores
- An interactive Plotly zodiac chart (HTML)
- Strength and stress word clouds derived from planet–sign–house trait mappings

The web frontend at `/` provides a form to enter birth data and displays all results in a tabbed interface (chart data, zodiac wheel, word clouds).

## Quick start (local development)

```bash
# 1. Install dependencies (Python 3.11+)
pip install -r requirements.txt

# 2. Download Swiss Ephemeris data files (one-time, ~28 MB)
python scripts/download_ephemeris.py

# 3. Run the API
uvicorn app.main:app --reload
```

Then open `http://localhost:8000` for the web UI, or `http://localhost:8000/docs` for the interactive API documentation.

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web frontend UI |
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

---

## Deployment architecture

```
GitHub (push to main)
  └─ GitHub Actions workflow (.github/workflows/deploy.yml)
       ├─ Authenticates to GCP via Workload Identity Federation (no service account keys)
       ├─ Builds Docker image
       ├─ Pushes to Artifact Registry (us-central1-docker.pkg.dev)
       └─ Deploys to Cloud Run (public URL, port 8080, 1Gi memory)
```

Every push to `main` triggers an automatic build and deploy. No manual steps required.

## GCP one-time setup (already completed)

These steps were done once to set up the infrastructure. Documented here for reference.

### 1. GCP project

- **Project name**: `hereandnowinunity`
- **Project number**: `984853982769`
- Created via Google Cloud Console, billing linked

### 2. APIs enabled

Enabled via **APIs & Services > Library**:
- Cloud Build API
- Cloud Run Admin API
- Artifact Registry API

### 3. Artifact Registry

Created via **Artifact Registry > Create Repository**:
- Name: `astro-chart`
- Format: Docker
- Region: `us-central1`

### 4. Workload Identity Federation

This allows GitHub Actions to authenticate to GCP without storing service account keys as secrets. Set up via **IAM & Admin > Workload Identity Federation**:

- **Pool name**: `github-pool`
- **Provider name**: `github-provider`
- **Provider type**: OpenID Connect (OIDC)
- **Issuer URL**: `https://token.actions.githubusercontent.com`
- **Attribute mappings**:
  - `google.subject` → `assertion.sub`
  - `attribute.repository` → `assertion.repository`
- **Attribute condition**: `assertion.repository == "sravya267/hereandnowinunity"` (restricts access to this repo only)

### 5. IAM permissions

Configured via **IAM & Admin > IAM**:

**Workload Identity principal** (`principalSet://iam.googleapis.com/projects/984853982769/locations/global/workloadIdentityPools/github-pool/attribute.repository/sravya267/hereandnowinunity`):
- Cloud Build Editor
- Cloud Run Admin
- Artifact Registry Writer
- Service Account User

**Compute Engine default service account** (`984853982769-compute@developer.gserviceaccount.com`):
- Artifact Registry Writer (needed because the WIF principal acts as this service account)

**Cloud Build service account** (`984853982769@cloudbuild.gserviceaccount.com`):
- Cloud Run Admin
- Service Account User

### 6. GitHub repository secrets

Set via **Settings > Secrets and variables > Actions**:

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | `hereandnowinunity` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/984853982769/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | `984853982769-compute@developer.gserviceaccount.com` |

---

## What was built and why

### Web frontend (`app/static/index.html`)

The original repo was a pure API with no UI. We added a single-page HTML frontend served by FastAPI at `/` so users can interact with the service through a browser. It includes:
- A form for birth date, time, location, and zodiac system
- Tabbed results: chart data table, interactive zodiac wheel (Plotly via iframe), and word cloud image
- All three API calls (`/chart`, `/chart/wheel`, `/chart/wordcloud`) fire in parallel for speed
- Dark theme with responsive design, loading spinner, and error handling

### FastAPI static file serving (`app/main.py`)

Updated `app/main.py` to:
- Mount `/static` directory using `StaticFiles`
- Serve `index.html` at `GET /` via `FileResponse` instead of the old JSON response
- No separate web server needed — FastAPI serves both the API and the frontend

### GitHub Actions CI/CD (`.github/workflows/deploy.yml`)

Automated deployment pipeline that runs on every push to `main`:
1. Checks out the code
2. Authenticates to GCP using Workload Identity Federation (keyless, more secure than service account JSON keys)
3. Builds the Docker image and tags it with the commit SHA
4. Pushes to Artifact Registry
5. Deploys to Cloud Run with public access

### Ephemeris download fix (`scripts/download_ephemeris.py`)

Two files (`seleapsec.txt`, `ast0/se02060.se1`) were removed from the upstream swisseph GitHub mirror, causing Docker builds to fail. We split the file list into required and optional — the 5 core files (planets, moon, asteroids, star names, fixed stars) are required; leap seconds and the Chiron asteroid file are optional and log a warning instead of failing the build.

### Docker optimization (`.dockerignore`, `.gcloudignore`)

Added ignore files to exclude tests, markdown files, git history, and other unnecessary files from the Docker build context and `gcloud` uploads. Reduces build time and image size.

## Project structure

```
hereandnowinunity/
├── app/
│   ├── main.py              # FastAPI entrypoint, serves frontend + API
│   ├── config.py            # Settings (paths, env vars)
│   ├── static/
│   │   └── index.html       # Web frontend (single-page app)
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
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD: build + deploy to Cloud Run
├── Dockerfile               # Multi-stage build for Cloud Run
├── .dockerignore
├── .gcloudignore
└── requirements.txt
```

## License

The Swiss Ephemeris is dual-licensed (AGPL-3.0 or commercial). This project follows AGPL-3.0 in line with `pyswisseph`.
