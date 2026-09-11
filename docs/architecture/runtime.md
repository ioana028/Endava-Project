# Local Runtime and Configuration

## Required local services

| Service | Port | Development command target |
|---|---:|---|
| Frontend | 5173 | Vite dev server |
| Backend | 8000 | Uvicorn with reload |

The target one-command startup is:

```text
docker compose up --build
```

Docker Compose is a Day 1 platform deliverable. Until it exists, frontend and
backend may be started separately with their native tools.

## Environment

Copy `.env.example` to `.env` at the repository root. Current variables are:

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | Runtime name, normally `development` |
| `PORT` | Backend port, normally `8000` |
| `FRONTEND_PORT` | Frontend port, normally `5173` |
| `OPENAI_API_KEY` | Backend-only OpenAI credential |
| `GOOGLE_SERVER_API_KEY` | Backend-only Google Routes, Geocoding, and later Places credential |
| `VITE_GOOGLE_MAPS_BROWSER_KEY` | Frontend Google Maps JavaScript key, restricted to local/frontend origins |
| `CORS_ORIGINS` | Comma-separated allowed browser origins |

Never put `OPENAI_API_KEY` or `GOOGLE_SERVER_API_KEY` in frontend source,
Vite-exposed variables, JSON fixtures, logs, or committed files. The browser
Maps key is intentionally Vite-exposed and must be restricted by HTTP referrer
to the allowed frontend origins. `.env` is ignored by Git; `.env.example`
contains placeholders only.

## Health and startup behavior

`GET /health` must remain available even when external providers are down. A
healthy process means the local API is running, not that OpenAI or routing is
reachable. Provider failures should be reported by the relevant feature with a
stable API error.

## CORS

Development CORS must allow the origins in `CORS_ORIGINS`, initially:

```text
http://localhost:5173
http://127.0.0.1:5173
```

Do not use wildcard origins with credentials. Keep CORS configuration in
backend settings rather than hard-coding it in route modules.

## Data loading

The first fixtures are:

- `data/vehicles/telemetry.json`: Honda E demo vehicle, BEV, 42% battery,
  95 km estimated range, summer tyres.
- `data/partners/partners.json`: Ionity Győr, Hungarian e-vignette, and a
  Budapest restaurant offer.

Load fixtures through a small repository/loader boundary. Do not let each
endpoint open and interpret JSON independently.