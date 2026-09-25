# Google API Cost Controls

The Google Routes and Places providers use process-local request coalescing and short-lived TTL caches. Identical requests made concurrently or repeatedly during a demo share one upstream request.

## Current safeguards

- Geocodes are cached for one hour.
- Routes are cached for five minutes using origin, destination, priority, and waypoint coordinates.
- Places searches are cached for five minutes using category, location, preference, route geometry, and nearby coordinates.
- Route Places searches are hard-capped at four sample points, regardless of the environment value.
- Charger direction validation is hard-capped at six Compute Routes checks.
- Default charger amenities use three searches: food, coffee, and rest. Additional categories are searched only when explicitly requested.
- Charging searches request only charging fields. Attraction and general searches do not request photos or editorial summaries, avoiding unnecessary Atmosphere data.

## Operational rules

- Keep `GOOGLE_PLACES_MAX_SEARCH_POINTS=4` in local and demo environments.
- Do not add retry loops around Google provider calls without exponential backoff and request deduplication.
- Watch Google Cloud quota dashboards for Routes ComputeRoutes and Places Text Search separately.
- Keep the browser Maps JavaScript key restricted by HTTP referrer and the server key restricted by API and server IP where possible.

The caches are intentionally in memory for the single-process demo. A multi-worker or deployed service would need a shared cache such as Redis to coalesce requests across workers.
