# Day 9 Runtime and Provider Configuration

## Scope

This document covers the Person D runtime responsibilities for Day 9: provider resilience, deterministic route weather, country-rule coverage, and startup/health behavior. It intentionally excludes Person A, B, and C work.

## Runtime responsibilities

Person D owns:

- Google Maps route and Places adapters
- local weather provider behavior
- route-country and vignette rule enforcement
- environment configuration and startup checks
- provider health and resilience diagnostics
- local Docker startup and health continuity when remote providers are unavailable

## Environment defaults

The backend loads configuration from the repository root `.env` file. The current Day 9 defaults are:

```env
WEATHER_PROVIDER=offline
WEATHER_ENABLED=true
WEATHER_API_KEY=
WEATHER_TIMEOUT_SECONDS=10
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`WEATHER_PROVIDER` remains offline by default to preserve a reliable local demo without leaking secrets or depending on a live provider. `WEATHER_API_KEY` stays empty unless a real weather service is explicitly configured. `WEATHER_ENABLED` allows the platform to remain healthy in local-only mode.

## Weather provider behavior

The weather provider is a deterministic offline implementation suitable for local development and demo use.

It supports:

- sampling route points or a route corridor
- location and condition normalization
- temperature and severity handling
- weather alert conversion for warnings and critical conditions
- graceful fallback when no live weather data is configured

Severe conditions are converted into structured weather alerts while the rest of the route still remains usable. The provider does not invent remote facts; it works from deterministic fixture data and keeps the route planner operational even when the provider is unavailable.

## Country and vignette rules

The route-country rules cover Day 9 requirements including:

- Austria -> Hungary
- Czechia -> Slovakia
- Slovakia -> Slovenia

The alias matching stays explicit and avoids broad substring matching that can produce false positives. This keeps border detection safe and deterministic for Europe-focused route planning.

## Health and startup behavior

`GET /health` remains available on the backend regardless of provider state. `GET /health/config` reports only non-secret configuration state, including whether weather is enabled and whether a provider is configured.

The platform continues to be usable when:

- OpenAI is disabled
- Google routing is unavailable
- Google Places is unavailable
- weather is disabled or offline

## Local and Docker startup

Local startup remains:

```bash
docker compose up --build
```

The backend is expected to remain reachable on port 8000 and the frontend on port 5173. The runtime must still report health and allow local route planning flows even without remote services.

## Validation

Person D validation is limited to Person D-owned files and runtime behavior:

- configuration loads without secrets leakage
- overflow and fallback behavior remain safe when providers are unavailable
- country aliases and vignette rules are deterministic
- startup and health checks remain available in local-only mode
- weather behavior degrades gracefully rather than breaking route planning
