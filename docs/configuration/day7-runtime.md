# Day 7 runtime and provider reliability

## Runtime boundaries

Person D owns the backend runtime layer and the provider safety contract. The demo stays local-only and must remain self-serve when a remote provider is unavailable.

## Scenic capability rules

- `RoutePriority.SCENIC` is a distinct route preference and must not silently behave like `FASTEST`.
- If Google routing is configured and supports scenic routing, the provider request uses the route preference that matches the declared provider capability.
- If the provider is unavailable or cannot answer scenic data, the system must fall back to a deterministic offline scenic estimate and clearly label the result as an estimate.
- Scenic metadata must never claim a guaranteed scenic view or road quality unless the provider explicitly returned that fact.

## Provider diagnostics

`GET /health/config` exposes only non-secret runtime state:

- whether OpenAI is configured;
- whether Google routing is configured;
- whether Google Places is configured;
- which places provider resolved (`google` or `offline`);
- whether scenic capability is available;
- whether the partner enrichments fixture set is loaded.

No secrets or raw provider payloads are returned by this endpoint.

## Bounded provider fan-out

Route and Places calls remain bounded by the runtime settings:

- `GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_KM` / `GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_METERS`
- `GOOGLE_PLACES_NEARBY_SEARCH_RADIUS_METERS`
- `GOOGLE_PLACES_SAMPLE_INTERVAL_KM`
- `GOOGLE_PLACES_MAX_SEARCH_POINTS`

These values prevent unbounded route/Places searches and keep demo behavior deterministic.

## Error handling

- route and POI failures remain behind stable API error envelopes;
- provider timeouts and malformed payloads log compact diagnostics only;
- Docker Compose and local startup continue to work even when external providers are absent.

## Required validation

Before shipping Day 7, verify:

1. `start_driving` returns a 200 response with the active route state and rejects stale route IDs.
2. `/health/config` reports scenic and partner-enrichment readiness without exposing secrets.
3. provider failures surface as stable errors rather than stack traces.
4. the app starts cleanly with `docker compose up --build` or the equivalent local backend/frontend boot path.
