# Day 6 runtime and performance guide

## Runtime contract

Person D owns backend runtime instrumentation and provider boundaries.

The backend logs timing spans for the main runtime steps without exposing raw provider payloads or credentials:

- `session_secret_request_ms`
- `microphone_permission_ms`
- `peer_connection_ms`
- `data_channel_open_ms`
- `assistant_ready_ms`
- `geocode_ms`
- `route_provider_ms`
- `charging_lookup_ms`
- `total_route_plan_ms`
- `tool_call_ms`

These spans are informational and must never include API keys, audio blobs, request bodies, or raw Google/Places payloads.

## Local runtime assumptions

- The browser and backend are both local-only and should start with `docker compose up --build` or the equivalent dev server commands.
- A missing Google API key should resolve the Places layer to offline fixtures without crash conditions.
- Route planning must avoid unbounded provider fan-out by bounding sample points and deduplicating results.
- Charging lookups must use the route corridor and route-relative radius rather than unbounded cross-route queries.

## Provider safety rules

- Keep provider keys server-side only.
- Log only compact latency facts and stable identifiers.
- Never log raw provider JSON, geocoding payloads, or audio chunks.
- Keep route sampling deterministic and bounded.

## Demo targets

- Suzanne ready: p50 under 2 seconds after start.
- Core offline route facts: p50 under 3 seconds.
- Route/charging requests must remain bounded and not fan out to arbitrary provider calls.
