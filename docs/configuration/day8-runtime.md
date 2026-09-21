# Day 8 runtime and provider reliability

## Runtime boundaries

Person D owns the backend runtime layer, provider adapters, configuration, and operational safety checks for Day 8. The demo remains local-first and resilient when remote services are unavailable.

## Provider identity and normalization

- provider identity must stay stable at the adapter boundary and never apply partner policy inside a Google or Places adapter;
- brand names are normalized deterministically before any matching logic is applied;
- string display names, provider-brand aliases, and route-stop names remain distinct inputs that can be compared without broad fuzzy matching;
- place IDs and stable names remain available for diagnostics without exposing raw provider payloads to the voice layer.

## Bounded provider fan-out

- route and Places searches remain bounded by the configured search radii and sample intervals;
- multi-stop charging requests preserve the route order and waypoint sequence given by the deterministic planning step;
- provider failures degrade to stable service errors instead of leaking stack traces, credentials, or raw route geometry.

## Health and startup safety

`GET /health/config` should report only non-secret runtime state:

- whether OpenAI is configured;
- whether Google routing and Places are configured;
- which places provider resolved (`google` or `offline`);
- whether the scenic capability is available;
- whether partner-enrichment fixtures are ready.

If the partner fixture set is missing or malformed, the app should still boot cleanly and continue to serve health endpoints with safe degraded values.

## Required Day 8 validation

Before considering the Person D Day 8 work complete, verify:

1. provider identity remains stable for charging and place results;
2. route and Places fan-out remains bounded by runtime settings;
3. `/health/config` reports readiness without exposing secrets;
4. a multi-stop confirmed route preserves waypoint ordering when the routing provider receives the charging sequence;
5. local startup and health checks continue to work even when enrichment metadata is unavailable.
