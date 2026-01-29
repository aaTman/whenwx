# WhenWX

**When will the weather...?**

A web application that predicts when specific weather conditions will occur at a given location, using ECMWF IFS 15-day forecast data.

## Features

- **Location Input**: Enter coordinates manually or use browser geolocation
- **Weather Events**: Select from predefined weather thresholds (currently: freezing temperatures < -10°C)
- **Timing Results**: See when the condition will first occur, how long it will last, and model confidence
- **Beautiful UI**: Animated gradient background with a clean, modern design

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA PIPELINE                           │
│  Earthmover Arraylake (ECMWF IFS) → Processing Job → GCS Zarr  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           API LAYER                             │
│  xpublish (FastAPI) on Fly.io - Rate limited: 1 req/min        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                               │
│  React SPA on GitHub Pages                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Vite + React + TypeScript |
| Backend | Python (xarray, zarr, arraylake) |
| API | FastAPI + xpublish on Fly.io |
| Storage | Google Cloud Storage (zarr) |
| Hosting | GitHub Pages (frontend) |

## Project Structure

```
whenwx/
├── frontend/          # React TypeScript app
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── pages/        # Page components
│   │   ├── config/       # Weather event definitions
│   │   └── types/        # TypeScript interfaces
│   └── ...
│
├── backend/           # Python data processing
│   └── src/
│       ├── processors/   # Weather event processors
│       ├── pipeline/     # Data ingestion & export
│       └── main.py       # Processing entry point
│
├── api/               # xpublish API server
│   └── src/
│       ├── plugins/      # Custom xpublish plugins
│       ├── middleware/   # Rate limiting
│       └── main.py       # FastAPI app
│
└── .github/
    └── workflows/     # CI/CD pipelines
```

## Development

This project uses `uv` for Python dependency management.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:3000

### API (Demo Mode)

```bash
cd api
uv sync                                                    # Install dependencies
DEMO_MODE=true uv run uvicorn src.main:app --reload        # Start server
```

Visit http://localhost:8000/docs

### Backend Processing

```bash
cd backend
uv sync                                                    # Install dependencies

# Test with mock data
uv run python -m src.main --mock --local ./output.zarr
```

## Deployment

### Frontend (GitHub Pages)

Push to `main` branch triggers automatic deployment via GitHub Actions.

### API (Fly.io)

```bash
cd api
fly deploy
```

### Processing (GitHub Actions)

Runs automatically every 6 hours via scheduled workflow, or manually via workflow dispatch.

## Configuration

### Environment Variables

**API:**
- `GCS_BUCKET` - GCS bucket for zarr data
- `DEMO_MODE` - Use mock data (true/false)
- `RATE_LIMIT` - Rate limit string (e.g., "1/minute")
- `CORS_ORIGINS` - Allowed CORS origins

**Backend:**
- `ARRAYLAKE_TOKEN` - Earthmover Arraylake API token
- `GCS_BUCKET` - Output bucket
- `GOOGLE_CLOUD_PROJECT` - GCP project ID

**Frontend:**
- `VITE_API_URL` - API base URL

## Adding New Weather Events

1. Add event config in `backend/src/config.py`:
```python
WeatherEventConfig(
    event_id='heavy-rain',
    variable='tprate',
    threshold=0.00278,  # ~10 mm/hr
    operator='gt',
    ...
)
```

2. Add frontend event in `frontend/src/config/events.ts`:
```typescript
{
  id: 'heavy-rain',
  name: 'Heavy Rain',
  ...
}
```

3. Add API event in `api/src/plugins/weather_router.py`

## Data Sources

- **ECMWF IFS 15-day forecast** via [Earthmover Arraylake](https://earthmover.io)
- Updated ~4x daily (00Z, 06Z, 12Z, 18Z cycles)

## License

MIT
