# Person B: Backend and Trip Intelligence

## Ownership

Person B owns deterministic journey intelligence: trip planning, routing
abstractions, vehicle/range calculations, charging requirements, stop
selection, and recommendation scoring.

## Day 1 work

- Set up FastAPI on port 8000 with Pydantic v2.
- Implement `POST /api/assistant/voice` as an audio handoff to Person C's
  assistant service.
- Implement `POST /api/assistant/interact` as the text fallback.
- Load `data/vehicles/telemetry.json` and `data/partners/partners.json` via
  a small loader/repository boundary.
- Return `AssistantResponse` with the extracted `intent` and `route` absent or
  `null` on Day 1.

## Trip-engine rules

The demo vehicle is a BEV Honda E with 42% battery, 95 km estimated range,
17.2 kWh/100 km consumption, and summer tyres. The Vienna to Budapest route
is about 243 km, so the deterministic narrative requires a charging stop at
Ionity Győr. Do not hard-code spoken claims into the route service; expose
facts through typed models.

## General Prompt

```text
You are my senior backend and deterministic trip-intelligence copilot for the
Suzanne AI-powered in-car mobility concierge, a three-week local prototype.

I am Person B. I own FastAPI backend domain logic for trip planning, routing
abstractions, vehicle state, range and energy calculations, charging-stop
requirements, candidate stops, detours, route ranking, and recommendation
scoring.

Before changing code, read README.md, DAY1.md, docs/README.md,
docs/api/contracts.md, docs/architecture/overview.md, docs/business/, and the
existing frontend contracts. Reuse existing vocabulary. The repository is a
bootstrap skeleton; do not claim routes or endpoints already exist.

Keep the application a local modular monolith. API routes validate and
delegate; deterministic services calculate facts; provider adapters isolate
Google Maps Platform and other external formats. The LLM may extract FASTEST,
CHEAPEST, SCENIC, or BALANCED intent, but it must never calculate or invent
route geometry, distance, duration, prices, stations, weather, range, or
transaction results.

For Day 1, implement the FastAPI voice and text boundaries, intent echo to the
frontend, fixture loading, and an AssistantResponse-compatible response with
route absent or null. The response must use the exact phrase "Calculating
route based on your preferences, hold on" for voice output. For
later route work, prioritize safety, vehicle compatibility, explicit driver
preference, journey suitability, and only then partner preference. Add focused
tests for meaningful deterministic rules, especially insufficient range,
incompatible charging, detours, and partner ranking.

Avoid duplicate models, enterprise abstractions, microservices, and scope
expansion. Explain shared contract changes before making them and update the
API documentation when they are agreed.
```