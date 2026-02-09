# WhenWX

**When will the weather...?**

A web application that predicts when specific weather conditions will occur at a given location, using ECMWF IFS 15-day forecast data served on-demand from [Earthmover Arraylake](https://earthmover.io).

## Features

- **Custom Thresholds**: Choose a weather variable (Temperature, Wind Speed, Precipitation), set any threshold, and pick above/below
- **Location Input**: Enter coordinates manually or use browser geolocation
- **Timing Results**: See when the condition will first occur, how long it will last, and the next occurrence
- **Interactive Forecast Chart**: Recharts-powered line plot with threshold shading, "Now" marker, and hover tooltips showing valid time in local timezone
- **On-Demand Computation**: Each query reads a single point from Arraylake in ~2 seconds — no batch processing needed

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       DATA SOURCE                               │
│  Earthmover Arraylake (ECMWF IFS 15-day forecast)              │
└─────────────────────────────────────────────────────────────────┘
                                │
                          on-demand query
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           API LAYER                             │
│  FastAPI (xpublish) on Fly.io — rate limited: 5 req/min        │
│  Computes metrics + time series for a single lat/lon point     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                               │
│  React 19 + TypeScript + Vite on GitHub Pages                  │
│  Recharts for interactive forecast visualization               │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Vite + React 19 + TypeScript + Recharts |
| Backend | Python (xarray, arraylake, timezonefinder) |
| API | FastAPI + xpublish on Fly.io |
| Data | Earthmover Arraylake (ECMWF IFS) |
| Hosting | GitHub Pages (frontend), Fly.io (API) |

## Project Structure

```
whenwx/
├── frontend/          # React TypeScript app
│   ├── src/
│   │   ├── components/   # UI components (ThresholdBuilder, ForecastChart, etc.)
│   │   ├── hooks/        # useWeatherQuery (fetch + cache)
│   │   ├── pages/        # Home, Results
│   │   ├── config/       # variables.ts (extensible variable registry)
│   │   └── types/        # TypeScript interfaces
│   └── ...
│
├── api/               # xpublish API server
│   └── src/
│       ├── plugins/      # weather_router.py (query endpoint)
│       ├── middleware/   # Rate limiting (SlowAPI)
│       ├── variables.py  # Variable registry + unit conversions
│       ├── on_demand.py  # Single-point computation from Arraylake
│       └── main.py       # FastAPI app
│
└── .github/
    └── workflows/     # CI/CD (GitHub Pages deploy)
```

## Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173/whenwx/

### API (Demo Mode)

```bash
cd api
uv sync
DEMO_MODE=true uv run uvicorn src.main:app --reload
```

Visit http://localhost:8000/docs

## Deployment

### Frontend (GitHub Pages)

Push to `main` triggers automatic deployment via GitHub Actions.

### API (Fly.io)

```bash
cd api
fly deploy
```

## Configuration

### Environment Variables

**API (set in `api/fly.toml`):**
- `ARRAYLAKE_TOKEN` — Earthmover Arraylake API token (set as Fly secret)
- `RATE_LIMIT` — Rate limit string (default: `5/minute`)
- `CORS_ORIGINS` — Allowed CORS origins
- `ON_DEMAND_MODE` — Use on-demand Arraylake computation (default: `true`)
- `DEMO_MODE` — Use mock data for local dev (default: `false`)

**Frontend:**
- `VITE_API_URL` — API base URL (default: `http://localhost:8080`)

## Adding a New Weather Variable

1. Add to the backend registry in `api/src/variables.py`:
```python
_register(VariableConfig(
    id='dewpoint',
    label='Dewpoint',
    ecmwf_variables=['2d'],
    display_unit='°C',
    storage_unit='K',
    to_display=_kelvin_to_celsius,
    to_storage=_celsius_to_kelvin,
))
```

2. Add to the frontend registry in `frontend/src/config/variables.ts`:
```typescript
{
  id: 'dewpoint',
  label: 'Dewpoint',
  ecmwfVariable: '2d',
  defaultThreshold: 15,
  defaultOperator: 'gt',
  displayUnit: '°C',
  min: -40, max: 40, step: 1,
  convertToBackend: (c) => c + 273.15,
  convertFromBackend: (k) => k - 273.15,
}
```

That's it — the variable will appear in the dropdown automatically.

## Data Sources

- **ECMWF IFS 15-day forecast** via [Brightband](https://www.brightband.com/) + [Earthmover Arraylake](https://earthmover.io)
- Updated ~4x daily (00Z, 06Z, 12Z, 18Z cycles)

## License

MIT
