# Day 3: Automatic Journey Stops and Route-Aware POIs

## Goal

Extend the Day 2 Realtime route conversation so Suzanne automatically makes a
route safe and complete for the vehicle, then supports spoken requests for
route-aware places such as charging, hotels, restaurants, and attractions.

The primary EOD flow is:

```text
Driver presses Start Suzanne
  -> Realtime session connects over WebRTC
  -> Driver requests a route
  -> plan_route calculates the route and inspects vehicle range and countries
  -> backend automatically adds a suitable charging stop when required
  -> backend detects border crossings and toll/vignette requirements
  -> backend recalculates the final route through the charging stop
  -> frontend displays the final route, requirements, and charging stop
  -> Suzanne speaks only verified final route facts
  -> Driver may ask for another POI near the route, stop, or destination
```

Charging is mandatory when the vehicle cannot safely complete the journey. It
is not an optional confirmation flow and must not wait for the driver to say
"Add a charging stop". The driver may ask for another charger after the
automatic selection. Generic POIs are optional and must not change the route
unless the driver explicitly asks to add or route through one.

## Non-negotiable rules

- Keep `plan_route` as the primary Day 3 flow; do not duplicate its mandatory
  charging decision in a second tool.
- The LLM selects capabilities and supplies intent only. Deterministic services
  own route, range, charging, border, toll/vignette, POI, partner, distance,
  duration, detour, and availability facts.
- Automatically add a charging stop when the vehicle cannot safely complete
  the route with its current estimated range and safety buffer.
- Detect route countries and border crossings and derive toll/vignette
  requirements from deterministic route and country data, not partner data.
- `data/partners/partners.json` is optional enrichment. The Hungarian vignette
  entry has no partner benefit and must be narrated as a route requirement, not
  as a discount or commercial offer.
- Never infer partner status from Google Places data. Match partners by stable
  ID first and use cautious fallback matching only as tested.
- Never invent availability, compatibility, price, discount, detour, distance,
  duration, border, toll, vignette, booking, or payment success.
- Keep the full final `RouteResponse` in backend/frontend state for the map.
  Send only compact spoken facts to Realtime.
- Do not add a charging button, confirmation card, second TTS pipeline, wake
  word, automatic microphone start, or browser-side provider calls.
- Stop must close Realtime, stop microphone tracks, cancel pending work, and
  prevent late results from updating the UI or model session.

## Compact Realtime result

The browser may receive the full route for rendering, but the result returned
to Realtime must contain only facts Suzanne needs to speak:

```json
{
  "status": "success",
  "destination": "Budapest",
  "distanceKm": 251,
  "drivingDurationMinutes": 165,
  "totalDurationMinutes": 190,
  "chargingStop": {
    "name": "Ionity Győr",
    "detourMinutes": 4,
    "partnerBenefit": "15% partner rate"
  },
  "borderCrossings": ["Austria-Hungary"],
  "routeRequirements": ["Hungarian motorway vignette"]
}
```

Omit fields when the corresponding facts do not exist. The Hungarian vignette
may be matched to the partner fixture for future commerce, but its partner
entry has no benefit and must not produce one in this result.

## Shared contract direction

Person B owns the shared backend contract. Extend the canonical route model so
it can distinguish driving duration from total journey duration, a mandatory
charging stop from an optional POI, detected border crossings, mandatory toll
or vignette requirements, and optional partner enrichment.

Keep generic place data separate from partner enrichment. A `StopPinpoint` may
be useful without a partner, and a partner record must never make a stop
mandatory by itself.

## Person A: Frontend and route HMI

### Build today

- Keep the existing Start/Stop Realtime lifecycle unchanged.
- Render the final `plan_route` geometry, including an automatic charging
  waypoint when required.
- Show the selected charging stop, detour, and partner benefit only when a
  benefit is actually returned.
- Show border crossings and toll/vignette requirements as structured route
  facts. Do not label the Hungarian vignette as a partner discount.
- Distinguish driving time from total time when charging is included.
- Add voice-driven generic POI results for hotels, restaurants, attractions,
  charging, coffee, rest, and service without a selector or confirmation card.
- Show loading, no-suitable-charger, provider-error, and stale-result states.
- Keep full route data local and send only compact facts back to Realtime.

### Must not do

- Do not parse Suzanne's speech to determine route, stop, border, or toll state.
- Do not call Google Places or Google Routes from the browser.
- Do not add an on-screen charging confirmation or partner purchase control.

## Person B: Deterministic journey and POI services

### Build today

- Keep `plan_route` as the route entry point.
- Calculate safe charging search distance as
  `estimatedRangeKm - safetyBufferKm`, with the buffer configurable.
- Search, filter, and rank charging candidates deterministically. Safety,
  compatibility, route proximity, and detour precede partner preference.
- Automatically select and route through a suitable charger when required.
- Detect route countries and border crossings, then derive toll/vignette
  requirements from deterministic route/country rules.
- Enrich selected stops from `partners.json` only after suitability is
  established. The HU vignette fixture has no benefit.
- Add a provider-neutral generic POI search for charging, hotels, restaurants,
  tourist attractions, coffee, rest, and service.
- Rank generic POIs by route relevance, detour, requested preference, and
  quality. A non-partner POI remains valid.
- Recalculate through a POI only when the driver explicitly requests a route
  stop; finding a POI alone must not mutate the active route.

### Must not do

- Do not put ranking, border, toll, or charging logic in the LLM.
- Do not select a partner merely because it is a partner.
- Do not claim that the HU vignette has a discount or benefit.
- Do not put Google response formats in public contracts.
- Do not call OpenAI or live Google services from deterministic unit tests.

## Person C: Realtime conversation and AI integration

### Build today

- Keep `plan_route(destination, priority)` as the primary route tool.
- Never ask permission before a mandatory charging stop is added.
- Narrate final duration, charging stop, border crossing, and toll/vignette
  requirements only when returned by deterministic services.
- Add a generic `search_route_poi` tool for hotel, restaurant, attraction,
  charging, coffee, rest, and service requests.
- Mention a partner benefit only when one is returned. The HU vignette has no
  benefit and must be described only as a route requirement.
- Never claim a POI was added to the route unless a reroute result confirms it.

### Must not do

- Do not create a separate charging flow that duplicates `plan_route`.
- Do not put geometry, provider payloads, or the full route object in Realtime.
- Do not invent availability, discounts, detours, border crossings, tolls,
  vignettes, booking, or route facts.

## Person D: Google integrations and platform

### Build today

- Keep Routes and Geocoding behind provider-neutral adapters.
- Add Places adapters for charging and generic POI searches near the route,
  selected stop, or destination.
- Normalize provider results without leaking Google formats into public
  contracts.
- Ensure Routes accepts a selected charger or explicitly requested POI as a
  waypoint and returns updated geometry, distance, and duration.
- Provide route-country data needed for deterministic border and
  toll/vignette evaluation, with a clear local-test fallback.
- Keep backend keys private, configure timeouts, and mock providers in tests.
- Keep startup, CORS, health checks, and local fallback behavior working.

### Must not do

- Do not move deterministic ranking or route-requirement rules into adapters.
- Do not expose server credentials or call live providers from unit tests.

## API/tool boundary

The active Realtime session may call:

```text
plan_route(destination, priority)
search_route_poi(category, location, preference)
```

`plan_route` returns the final route, including automatic charging and route
requirements. `search_route_poi` returns a compact result and does not change
the active route unless the driver explicitly asks to add or route through it.

## Tests required

Use fake charging-search, POI, routing, country-rule, partner, and Realtime
providers. No unit test may call OpenAI, Google Places, or Google Routes.

Minimum coverage includes automatic charging, safety-buffer filtering,
deterministic ranking, charger waypoint recalculation, partner matching,
omission of the HU vignette benefit, border detection, toll/vignette rules,
generic hotel/restaurant/attraction/charging search, non-partner results,
compact Realtime results without geometry, provider failures, and
cancellation/stale-result behavior.

## End-of-day acceptance test

1. Start backend and frontend, then press Start Suzanne.
2. Say: `Take me to Budapest fast.`
3. Verify one `plan_route` call returns the final route without a charging
   confirmation question.
4. Verify vehicle range triggers an automatic suitable charging stop and the
   map displays recalculated geometry and the stop.
5. Verify Suzanne reports total duration and whether it includes charging.
6. Verify Suzanne detects the Austria-Hungary border and the Hungarian
   motorway vignette requirement.
7. Verify the vignette is not described as having a partner benefit.
8. Ask for a hotel near the route and an Italian restaurant near the
   destination without a second Start action.
9. Verify generic POI results work without a partner and do not mutate the
   route unless explicitly requested.
10. Verify provider failures, no suitable charger, Stop cancellation, and new
    session isolation.

## Definition of done

Day 3 is complete when one active Suzanne session automatically returns a safe
route with charging when required, identifies border and toll/vignette
requirements, displays and speaks the final verified journey facts, and
answers voice requests for route-aware charging, hotel, restaurant, and
attraction POIs without treating partner data as a prerequisite or inventing
benefits.
