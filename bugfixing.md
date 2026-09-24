# Suzanne Bugfixing Plan

## Purpose

This document is the single-owner implementation plan for stabilizing Suzanne before any new feature work begins.

The goal is to preserve Suzanne's current demo capabilities while making the system:

- cheaper and bounded when calling Google APIs;
- authoritative about route, origin, countries, vehicle, and charging facts;
- deterministic and explainable when selecting charging options;
- safe around bookings, confirmations, and dates;
- quieter, less repetitive, and more executive-assistant-like;
- polished from backend contract through frontend presentation.

This is a demo system, not a production deployment. The implementation should still use production-grade boundaries: typed contracts, explicit state transitions, bounded external calls, deterministic selection, and tests for every user-visible claim.

## Baseline and Branch

- Baseline branch: `main`.
- Working branch: `last-resort-bugfixing`.
- Existing cost work: branch `google-cost-fix`, commit `588cdd5` (`Reduce Google API request duplication and cost`).
- The cost branch contains:
  - `backend/app/core/async_cache.py`;
  - route and Places TTL/in-flight caching;
  - reduced Places fan-out and field masks;
  - charger validation limits;
  - cost-control documentation;
  - cache regression tests.

Before bug fixing begins, review and port the cost branch onto `last-resort-bugfixing` by cherry-picking `588cdd5` or applying an equivalent reviewed change. Do not reimplement the same safeguards independently. Run the full test suite immediately after the port.

Keep the existing `docs/` and `DAY*.md` files. They are the project baseline and contain useful product, architecture, API, and demo context. Do not delete or silently rewrite them.

## Non-Negotiable Product Rules

1. Suzanne is a high-level in-car executive assistant, not a general-purpose chatbot.
2. She speaks only authoritative returned facts. Missing facts are omitted, not guessed.
3. Google calls are bounded by route/session budgets and deduplicated by request fingerprint.
4. Search results are suggestions. A route changes only after explicit driver confirmation.
5. Charging options are numbered and unfixed until the driver chooses one.
6. Internal IDs, provider IDs, transaction IDs, and booking IDs are never spoken.
7. A booking is not confirmed until all required fields are valid and the backend returns a completed result.
8. The UI distinguishes pending, suggested, selected, validated, confirmed, and failed states.
9. A repeated request in the same active route session reuses the existing result.
10. Every spoken distance, duration, country, partner benefit, and charging fact must come from a typed contract field.

## Target Demo Flow

1. Driver says: `Hey Suzanne.`
2. Driver asks: `Plan the fastest route to Budapest.`
3. Suzanne gives one friendly route summary with origin, destination, duration, distance, countries, vignette requirement, and charging status.
4. The backend performs one bounded charging search and prepares one or two numbered suggestions in the background.
5. Suzanne says: `I found two suitable charging options. Option one is ... Option two is ... Which would you prefer?`
6. Driver says: `Choose option one.`
7. Backend validates only the selected charger with one waypoint route request, then confirms the route.
8. Suzanne reports the selected station, charging duration, route-time addition, and one concise verified partner benefit if present.
9. Driver asks: `Find attractions along the route.` Suzanne presents several map results but speaks only the best few.
10. Driver chooses an attraction and confirms the reroute.
11. Driver asks for a restaurant or hotel. Suzanne searches once, asks only for genuinely missing booking fields, and understands `tonight`.
12. Driver books. Suzanne says the booking is complete and details were sent to the phone app.
13. Driver asks for the vignette. Suzanne purchases only the current valid requirement and confirms without exposing IDs.
14. Driver says: `Let's get going.` The map enters navigation-style POV.

## Architecture Changes

### A. External request budget and deduplication

Port `google-cost-fix` first. Then add a session-level budget around the provider boundary:

```text
base route:             1 Routes request
geocoding:              0-2 requests, cached
charging discovery:     1 Places request
charger validation:     1 Routes request for the chosen option
POI search:             1 Places request per explicit user intent
POI reroute:            1 Routes request after confirmation
amenities:              1 bounded Places request or one bounded category batch
weather:                0 Google requests
```

Required implementation:

- keep TTL and in-flight coalescing from `google-cost-fix`;
- add a per-active-session request counter with a hard ceiling;
- include provider, method, route fingerprint, category, and reason in structured logs;
- reject or serve cached data when the budget is exhausted;
- never retry automatically without bounded exponential backoff and deduplication;
- never search all route sample points when Search Along Route can express the request;
- keep the default route sample maximum at four, preferably one for Search Along Route;
- use the smallest Places field mask that supports the UI and voice facts;
- keep partner matching local through `data/partners/partners.json`.

Acceptance:

- repeated identical route/Places calls make one upstream request;
- concurrent identical calls share one task;
- a complete demo remains below the configured session budget;
- tests fail if a new code path increases the expected Google call count.

### B. Canonical route session

Create one authoritative route-session model instead of spreading state across mutable fields and prompt assumptions.

The session must contain:

```text
session_id
route_id
origin
origin_coordinates
destination
destination_coordinates
priority
countries
border_crossings
route_requirements
route_status
charging_status
charging_options
selected_charging_option
confirmed_charging_plan
poi_searches
active_search_id
purchased_requirement_ids
booking_state
```

Use explicit status values:

```text
ROUTE_LOADING
ROUTE_READY
CHARGING_PENDING
CHARGING_OPTIONS_READY
CHARGING_OPTION_SELECTED
CHARGING_ROUTE_VALIDATED
CHARGING_CONFIRMED
POI_SEARCHING
POI_READY
REROUTING
BOOKING_PENDING
BOOKING_CONFIRMED
DRIVING
ERROR
```

Every tool response must carry the current `route_id` and, where relevant, `search_id` and `session_id`. A route mutation creates a new route ID and returns it to the frontend and Realtime model.

### C. Route facts, origin, and countries

Fix the provider contract so Google route responses populate country information whenever available. Do not infer intermediate countries from formatted address strings when a provider segment/country field is available.

Add an explicit origin field to route planning. For this demo it may default to Vienna, but the value must be represented as an authoritative route fact and spoken as the starting point.

Required route facts:

- origin name;
- destination name;
- distance in kilometres;
- driving duration;
- countries traversed;
- border crossings;
- vignette/toll requirements;
- charging requirement/status;
- weather summary when available.

Acceptance:

- Suzanne can answer `Where are we starting?` from returned facts;
- Suzanne can list countries and border crossings without guessing;
- reverse-direction and multi-country routes have tests;
- the spoken distance equals the typed route distance shown in the UI.

### D. Charging options, not automatic stops

The initial route must not silently add a charging stop. It should calculate and display one or two safe options:

```text
#1 Station name
   provider/network
   charging power
   estimated charging duration
   estimated route-time addition
   detour
   verified partner benefit, if local data confirms it

#2 Station name
   same facts
```

Requirements:

- option numbers are stable within the route session;
- Google Place IDs remain internal;
- option candidates must be within the current usable range or a valid later-leg range;
- charger compatibility and availability must be explicit fields;
- unknown compatibility is not silently treated as compatible;
- rank by safety first, then minimal route-time cost, charging power, detour, and stable provider ID;
- use route geometry/progress for initial filtering;
- validate only the selected option with Compute Routes;
- if selected validation fails, offer the second option and explain the failure without exposing API details;
- selecting an option never confirms it until the driver explicitly accepts;
- repeated selection of the same option is idempotent.

Acceptance:

- same route and telemetry produce the same option order;
- options are visible before confirmation;
- `Choose option one` maps to the correct stable candidate;
- selected validation makes exactly one bounded waypoint route call;
- confirmed charging stops appear as route markers and in the route summary;
- the assistant distinguishes suggested from confirmed charging.

### E. Vehicle and telemetry boundaries

Telemetry is internal planning input and a user-facing fact only when explicitly requested.

Add a typed vehicle capability model containing at minimum:

- usable current range;
- maximum post-charge range;
- consumption rate;
- connector types;
- maximum accepted charging power;
- vehicle battery capacity;
- current battery percentage.

Use the capability model for charger filtering and charging-time estimates. Do not let Suzanne narrate raw telemetry during route planning. If asked directly, answer only fields exposed by the contract.

### F. Voice orchestration and executive-assistant tone

The Realtime prompt and frontend event flow must use an authoritative-response protocol:

1. one short acknowledgement before a tool only when natural;
2. silence while the tool is pending;
3. one response after the tool result;
4. no correction-style responses caused by partial facts;
5. no technical processing narration;
6. no repeated station/network/partner wording;
7. no internal IDs;
8. no facts not present in the tool output.

Use response templates by state:

- route ready: friendly, one sentence, origin/destination/duration/countries/requirements;
- charging options ready: numbered options and one choice question;
- charging confirmed: station, duration, route-time addition, one benefit sentence;
- booking incomplete: ask only for missing fields;
- booking complete: details sent to phone app;
- error: concise actionable recovery.

Configure Realtime turn detection explicitly. Investigate server VAD, threshold, silence duration, prefix padding, noise reduction, and barge-in cancellation. Do not allow every `speech_started` event to interrupt a response without debounce or validated speech.

Acceptance:

- background noise does not repeatedly trigger a new turn in browser testing;
- Suzanne never speaks before the relevant Google result is authoritative;
- every successful tool call produces one concise response;
- interruption and cancellation behavior is covered by a browser test or documented manual test.

### G. Booking safety

Centralize date/time normalization and validation:

- `today` means the configured local date;
- `tomorrow` means the next local date;
- `tonight` means today at a configured default restaurant time;
- `yesterday` is rejected;
- ISO dates before today are rejected;
- invalid dates and impossible times are rejected;
- the clock/time zone is injectable in tests;
- booking completion is not announced until the wallet/backend returns completed or duplicate;
- incomplete booking requests remain `BOOKING_PENDING` and cannot produce a success message;
- booking requires current route, search, result, category, and explicit booking intent.

### H. POI inventory and distance correctness

Separate spoken recommendations from map inventory:

- return a larger bounded set, such as five to ten results;
- let deterministic selection rank and deduplicate results;
- Suzanne speaks only the top two or three unless asked for more;
- retain the ten-review minimum for attractions;
- preserve detour threshold and endpoint exclusions unless a new spec explicitly changes them;
- paginate or reveal additional results without another Google call when cached.

Replace overloaded fields:

```text
route_distance_km
straight_line_distance_km
route_offset_km
estimated_driving_detour_minutes
```

Never put kilometres in a `detour_minutes` field. Never ask the model to calculate distance from coordinates. If a provider has not returned a verified value, omit it.

## Ordered Work Packages

### Package 0: Baseline and cost controls

- Review and port `google-cost-fix` commit `588cdd5`.
- Run backend, frontend, and diff validation.
- Add session request budgets and structured provider logs.
- Record the expected Google call budget in tests.

### Package 1: Contracts and route session

- Define canonical route-session/status contracts.
- Add origin and country facts.
- Return current route/search/session IDs from every mutating tool.
- Remove duplicated route-state ownership where safe.
- Add contract tests before implementation changes.

### Package 2: Charging option workflow

- Replace automatic multi-candidate validation with one or two numbered suggestions.
- Add deterministic ranking and stable option IDs.
- Add selected-option validation and idempotent confirmation.
- Render unfixed suggestions and confirmed markers distinctly.
- Add backend and UI tests.

### Package 3: Vehicle capability and telemetry

- Add capability fields and charger compatibility rules.
- Keep raw telemetry out of normal voice facts.
- Add charger filtering tests for range, power, connector, availability, and unknown data.

### Package 4: Voice, VAD, and response authority

- Simplify Realtime instructions around state-specific templates.
- Configure turn detection and noise handling.
- Gate response generation on authoritative tool completion.
- Add event-order and browser/manual interruption tests.

### Package 5: Booking and commerce safety

- Centralize date/time normalization.
- Reject past dates.
- Introduce explicit booking intent state.
- Prevent premature success narration.
- Add booking contract and integration tests.

### Package 6: POIs, distances, and executive UI

- Expand bounded cached POI inventory.
- Correct distance/detour contracts.
- Show concise cards with progressive detail.
- Keep map overlays readable and non-blocking.
- Add deterministic POI and frontend presentation tests.

### Package 7: Demo hardening

- Run the complete demo flow repeatedly with external calls enabled and request logging active.
- Verify call counts against the session budget.
- Verify no duplicate tool calls, route resets, stale IDs, or premature claims.
- Run all automated checks.
- Update the relevant project documentation when behavior or contracts change.

## Required Test Matrix

### Backend unit tests

- country extraction and route facts;
- origin propagation;
- vehicle capability filtering;
- stable charging option ordering;
- option selection and idempotency;
- request budget enforcement;
- cache hit and in-flight coalescing;
- booking date/time validation;
- booking pending versus completed states;
- POI result inventory and distance units.

### Backend integration tests

- route tool returns authoritative pending/ready states;
- charging option selection returns a new route ID;
- vignette purchase after reroute uses the current route ID;
- hotel and restaurant booking require complete valid inputs;
- partner benefits come from local partner data;
- no duplicate provider call for repeated tool request.

### Frontend tests

- pending route state does not narrate final facts;
- charging option cards show stable `#1` and `#2` labels;
- selected versus confirmed marker styles differ;
- route facts and spoken facts match;
- booking success does not appear while fields are incomplete;
- navigation POV is stable after map initialization;
- no weather or suggestion overlay blocks the map.

### Manual acceptance run

Use one fresh route session and execute:

1. `Hey Suzanne.`
2. `Plan the fastest route from Vienna to Budapest.`
3. Ask for countries and starting point.
4. Choose charging option `#1`.
5. Ask for attractions and reveal more than three cached results.
6. Add one attraction.
7. Find a restaurant for tonight and book it for two.
8. Find a hotel for tonight and book it for two.
9. Purchase the required vignette.
10. Say `Let's get going.`
11. Repeat selected searches and confirm no unexpected Google calls.
12. Inspect structured logs and confirm the request budget was respected.

## Definition of Done

- Every one of the ten reported issues has a root-cause test or an explicit documented manual acceptance test.
- The full demo flow remains functional.
- Google requests are bounded, cached, logged, and budgeted.
- Suzanne speaks only authoritative facts and never exposes internal identifiers.
- The route session remains consistent after charging, POI reroutes, bookings, and vignette purchase.
- Backend tests, frontend lint, frontend build, and diff checks pass.
- The resulting changes are documented clearly, while the original `docs/` and `DAY*.md` files remain the project baseline.
