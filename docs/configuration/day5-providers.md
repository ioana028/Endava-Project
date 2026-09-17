# Day 5 Provider Configuration

Day 5 supports explicit provider selection through the repository root `.env`.
Copy `.env.example` to `.env` before starting the stack.

## Provider modes

- `PLACES_PROVIDER=offline` uses deterministic fixtures and never calls Google.
- `PLACES_PROVIDER=google` requires `GOOGLE_SERVER_API_KEY` and uses Google
  Routes, Geocoding, and Places adapters.
- `PLACES_PROVIDER=auto` selects Google when the server key is present and
  otherwise falls back to offline fixtures.

The browser map uses `VITE_GOOGLE_MAPS_BROWSER_KEY`. Keep this key restricted by
HTTP referrer. `OPENAI_API_KEY` and `GOOGLE_SERVER_API_KEY` remain backend-only.

## Day 5 policies

- Route attraction corridor: `GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_KM`, default
  `7.5` km and bounded to the configured provider request count.
- Charging-stop amenity radius: `GOOGLE_PLACES_NEARBY_SEARCH_RADIUS_METERS`,
  default `500` m.
- Route attraction searches exclude the first and last `10` km through named
  deterministic policy constants.
- Stop amenity searches are read-only and never add a waypoint or reroute.

## Manual provider acceptance

With valid local credentials, verify:

1. `GET /health/config` reports the intended Places provider without exposing
   credentials.
2. A route request returns provider-backed geometry, charging, toll, and
   requirement facts.
3. Route attraction results exclude the endpoint regions.
4. Destination attraction searches remain destination-centered.
5. Amenity searches around a selected charger stay within `500` m and preserve
   the active route.
6. Suzanne reports only facts returned by the provider-backed backend tools.

Automated tests use offline fixtures or mocked provider responses and never call
Google or OpenAI.
