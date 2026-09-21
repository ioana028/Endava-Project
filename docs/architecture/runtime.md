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
| `OPENAI_REALTIME_MODEL` | Realtime voice model, normally `gpt-realtime-2.1-mini` |
| `OPENAI_REALTIME_SECRET_SECONDS` | Lifetime of browser Realtime client secrets, normally `300` |
| `GOOGLE_SERVER_API_KEY` | Backend-only Google Routes, Geocoding, and later Places credential |
| `PLACES_PROVIDER` | `auto`, `google`, or explicit `offline` provider selection |
| `GOOGLE_PLACES_TIMEOUT_SECONDS` | Google Places request timeout |
| `GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_KM` | Route-corridor radius in kilometers, default 7.5 |
| `GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_METERS` | Route-corridor radius in meters, default 7500 |
| `GOOGLE_PLACES_NEARBY_SEARCH_RADIUS_METERS` | 500 m charging-stop search radius, default 500 |
| `GOOGLE_PLACES_SEARCH_RADIUS_METERS` | Backward-compatible alias for the route corridor radius |
| `GOOGLE_PLACES_SAMPLE_INTERVAL_KM` | Distance interval for route sampling |
| `GOOGLE_PLACES_MAX_SEARCH_POINTS` | Upper bound on route-corridor Places calls |
| `VITE_GOOGLE_MAPS_BROWSER_KEY` | Frontend Google Maps JavaScript key, restricted to local/frontend origins |
| `CORS_ORIGINS` | Comma-separated allowed browser origins |

Never put `OPENAI_API_KEY` or `GOOGLE_SERVER_API_KEY` in frontend source,
Vite-exposed variables, JSON fixtures, logs, or committed files. The browser
Maps key is intentionally Vite-exposed and must be restricted by HTTP referrer
to the allowed frontend origins. `.env` is ignored by Git; `.env.example`
contains placeholders only.

The backend exposes a short-lived Realtime client secret to the frontend through
`POST /api/assistant/realtime/session`. The frontend uses that secret only to
establish the user-started WebRTC session; it never receives `OPENAI_API_KEY`.
The Realtime session is configured server-side with the deterministic
`plan_route` tool. The browser sends tool arguments to
`POST /api/assistant/realtime/tools/plan-route`, which delegates to the existing
route service and returns the structured `RouteResponse`.

The voice tool lifecycle for route-aware POIs is:

1. Suzanne calls `search_route_poi`; search is read-only and returns factual
  suggestions.
2. Suzanne presents one or two returned suggestions without inventing ratings,
  amenities, availability, or detour values.
3. After the driver selects a suggestion, Suzanne states the proposed change
  and asks for explicit voice confirmation.
4. Only a clear acceptance invokes `reroute_through_poi` with the selected POI
  ID, the exact opaque active-route context, and `confirmation: "confirmed"`.
5. The route is considered changed only after a successful deterministic
  response. Realtime receives compact speech facts, never geometry or raw
  provider data.

The frontend preserves structured tool error codes and messages for concise
spoken error handling. Stopping voice closes the WebRTC session, aborts or
ignores late tool work, and does not by itself erase the last valid route or
POI suggestions. New route planning and successful rerouting explicitly
replace stale suggestion state.

## Health and startup behavior

`GET /health` must remain available even when external providers are down. A
healthy process means the local API is running, not that OpenAI or routing is
reachable. Provider failures should be reported by the relevant feature with a
stable API error.

`GET /health/config` reports only non-secret configuration state, including
whether backend credentials are present and whether Places resolved to Google
or the explicit offline provider. It never returns credentials or provider
payloads. Day 7 adds safe runtime diagnostics for scenic preference capability
and partner enrichment readiness without exposing secret material or raw Google
responses.

Day 7 reliability rules:

- if Google routing is unavailable, scenic requests must degrade to a labeled
  offline estimate instead of silently acting like `FASTEST`;
- route and Places searches remain bounded through a fixed sample interval, a
  maximum search count, and deduplicated provider results;
- provider error logs keep only latent timing and stable IDs, never raw JSON,
  credentials, or route geometry.

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
  Budapest restaurant offer. The vignette entry has no partner benefit; it is
  matched only as optional commerce enrichment for a deterministic route
  requirement.

Load fixtures through a small repository/loader boundary. Do not let each
endpoint open and interpret JSON independently.