# Day 4: Smart Route-Aware POI Discovery and Driver-Selected Rerouting

## Purpose

Day 4 advances Suzanne from a single-corridor demonstration into a genuinely
smart route assistant. The assistant must discover useful places from external
provider data, understand where those places are relative to the complete
route, present only the most relevant suggestions, and change the route only
after the driver explicitly asks and confirms that change.

The implementation must not replace real discovery with a new list of demo
locations. Vienna to Budapest remains the primary acceptance corridor, but it
is only an acceptance scenario. The code must work for other destinations,
route shapes, countries, and provider results without editing source code or
adding city-specific coordinates.

Day 4 extends the existing architecture:

```text
Driver speech
    -> OpenAI Realtime intent/tool selection
    -> FastAPI deterministic service
    -> Google Routes / Google Places adapters
    -> provider-neutral route and POI facts
    -> frontend map and route state
    -> compact facts returned to Suzanne
```

The LLM understands and communicates. Deterministic code fetches, validates,
filters, ranks, and calculates. The frontend renders structured facts. No layer
may invent provider data or silently change the route.

## Relationship to the roadmap and scope

Day 4 follows the existing product roadmap items for:

- generic route and POI cards;
- conversation follow-ups without losing the active route;
- future simulated toll payment and restaurant booking boundaries;
- optional rerouting through a driver-selected place;
- clear presentation polish after core route behavior works.

The existing scope remains in force:

- local React and FastAPI modular monolith;
- Google Maps Platform adapters for routes, geocoding, Places, and browser maps;
- OpenAI Realtime over WebRTC;
- deterministic backend facts and compact model context;
- flat JSON fixtures only for telemetry, partners, and offline tests;
- no remote database, microservices, production authentication, real payment,
  real booking, or autonomous driving.

Day 4 does not expand the product into a Europe-wide navigation platform. It
makes the current provider-backed route experience correct and reusable.

## Day 4 outcomes

At the end of Day 4, Suzanne must be able to:

1. Search for attractions, restaurants, hotels, charging, coffee, rest,
   toilets, fuel, and service locations along the complete active route.
2. Return real provider-backed results when Google Places is configured.
3. Use an explicit offline/test provider without embedding demo geography in
   application code.
4. Treat suitable petrol stations, convenience stores, and service areas as
   coffee or rest suggestions when provider data supports those amenities.
5. Avoid returning only places near the origin or destination when the driver
   asks for something along the route.
6. Return at most one or two useful suggestions per request.
7. Show those suggestions as clearly visible, selectable map markers and in a
   synchronized list.
8. Keep the active route unchanged while Suzanne is only searching.
9. Add a selected POI as a waypoint only after an explicit driver request and
   confirmation.
10. Preserve the destination and mandatory charging stops when rerouting.
11. Keep suggested POIs visible after the driver presses Stop. Stop ends voice
    capture and the Realtime session; it does not erase map state.
12. Reject stale selections and late provider responses safely.

## Product rules

### Provider-backed discovery

Production POI discovery must come from a provider adapter. The application
must not contain a hardcoded list of restaurants, cafes, hotels, attractions,
fuel stations, or route locations masquerading as live search results.

Allowed data sources:

- Google Places for live POI discovery;
- Google Routes and Geocoding for route context and rerouting;
- flat JSON fixtures for vehicle state, partner enrichment, and deterministic
  tests;
- an explicit offline provider used only when live Google configuration is
  absent or a test injects it.

The offline provider must be clearly named and documented. It must not be the
implicit production behavior when a Google key is available.

### No city-specific assumptions

Do not write code that assumes the route is Vienna to Budapest. Do not filter by
city names, use destination-city coordinates, or select a POI because its ID is
known from the demo. The route geometry and provider response are the only
geographic authority for route searches.

The default origin may remain configurable for the demo, but it must be read
from settings or a vehicle/session input. It must not be used by POI ranking as
a hidden special case.

### Suggestions versus route changes

A POI search is read-only:

- it returns suggestions;
- it does not add a waypoint;
- it does not mutate route geometry;
- it does not change duration, tolls, requirements, or mandatory stops.

A reroute is a separate explicit operation:

1. Suzanne searches and suggests one or two places.
2. The driver chooses a place by name, list selection, or marker selection.
3. Suzanne states the proposed route change and asks for voice confirmation.
4. Only after confirmation does the frontend call the reroute tool.
5. The backend validates the selected POI against the active route/search context.
6. Google Routes recalculates the route with the POI as a waypoint.
7. The new route replaces the old route only after a successful response.

There must be no silent rerouting because the driver asked for suggestions.

### Stop behavior

Pressing Stop means:

- close the Realtime connection;
- stop microphone and audio tracks;
- abort in-flight tool work where possible;
- ignore late tool responses;
- preserve the last valid route, POI markers, and route summary on screen.

A new route request may clear POIs that belong to the previous route before the
new route is displayed. A new POI search replaces the previous suggestion set.
An explicit clear action may remove suggestions. These events must not be
confused with Stop.

### Result count and diversity

The backend returns no more than two POIs for a normal voice request. The
frontend must not fetch ten results and hide eight of them as its primary
ranking strategy.

Results must be geographically diverse. Two suggestions that are effectively
at the same location should not occupy both result slots when a suitable place
exists elsewhere on the route. Ranking should consider:

- distance to the route corridor;
- estimated detour where available;
- position along the route;
- requested category and amenities;
- stated driver preference;
- rating and availability when provider data supplies them;
- spatial diversity;
- stable provider ID for deterministic tie-breaking.

All thresholds must be named configuration values or constants with tests. Do
not scatter unexplained values such as `3` or `0.35` through provider code.

## Provider and domain design

### Google Places adapter

The Google adapter belongs in:

`backend/app/integrations/places/google.py`

It must:

- receive an active provider-neutral route, not a city-specific route;
- sample the complete route at bounded distance intervals;
- query a bounded number of route corridor points;
- use a route-relative search radius;
- support destination searches separately from route searches;
- deduplicate by Google place ID;
- parse only fields needed by the domain contract;
- preserve provider-specific types internally for classification;
- return provider-neutral `StopPinpoint` or candidate objects;
- translate HTTP, timeout, malformed-response, and quota errors into a stable
  provider error;
- never expose API keys or raw provider payloads to the browser or Realtime.

Route sampling must be distance-based, not based only on the first, middle, and
last geometry vertices. A long route with sparse geometry and a short route
with dense geometry must both receive sensible coverage. The number of calls
must be bounded to control cost and latency.

The adapter should use a field mask containing only required fields, such as:

- place ID;
- display name;
- location;
- Google place types;
- rating when available;
- editorial summary or address when useful;
- known accessibility/opening/amenity fields only when the selected API
  contract supports them and the product actually uses them.

Do not pass raw Google JSON into domain services or frontend state.

### Categories and amenities

The public category vocabulary must be provider-neutral. Google types and text
queries are adapter details.

Minimum categories for Day 4:

- `attraction`;
- `restaurant` and `food`;
- `hotel`;
- `coffee`;
- `rest`;
- `toilets`;
- `fuel`;
- `charging`;
- `service`.

Petrol-station behavior is explicit:

- A fuel station is a valid `fuel` result when Google classifies it as a fuel or
  gas station.
- A fuel station may be returned for `coffee` only if Google also supplies a
  cafe, convenience-store, rest-area, food, or equivalent supporting type or
  amenity signal.
- A fuel station may be returned for `rest` when provider data supports rest,
  toilets, convenience, food, or service-area use.
- The assistant must say only what the provider returned. A fuel station type
  alone does not prove that coffee or toilets are available.
- The result should retain factual amenity labels so Suzanne can say, for
  example, "a fuel stop with a cafe" rather than inventing a facility.

If Google does not provide enough information to support a claim, return the
fuel result only for a fuel request or omit it from the coffee/rest ranking.

### Data and fixtures

Move generic fallback records out of Python provider modules. Intentional test
records belong under `data/` or test factories and must be visibly marked as
fixtures.

Do not add hardcoded POIs to make one acceptance test pass. If a test needs a
place, construct a small provider response in the test or load an explicit
fixture file. Tests must verify behavior, not the existence of a specific
commercial business.

Partner fixtures remain valid for optional enrichment. A partner relationship
must never be required for a useful POI result and must never influence route
safety. The Hungarian vignette remains a route requirement without a partner
benefit.

## Rerouting design

### Backend operation

Add a dedicated provider-neutral reroute operation, for example:

`POST /api/assistant/realtime/tools/reroute-through-poi`

The exact name may change during contract review, but it must be separate from
POI search and plan-route.

The request must contain only compact identifiers and intent fields, such as:

- selected POI ID;
- optional selected POI coordinates if required for lookup, validated against
  the active result;
- current route/session identifier or equivalent active-route context;
- route priority when it must be preserved.

The frontend must not send full Google payloads or arbitrary unvalidated
coordinates as an instruction to reroute.

The backend must:

- confirm the POI belongs to the current active route/search context;
- reject a POI from an old route or old session;
- reject invalid or unreasonable coordinates;
- preserve mandatory charging stops and their order;
- preserve the requested destination;
- call the routing provider with waypoints;
- recalculate geometry, distance, driving duration, total duration, tolls,
  borders, vignettes, alerts, and route requirements;
- return a complete replacement `RouteResponse` only on success;
- leave the old route available to the caller when rerouting fails.

The route service remains the owner of route facts. The API layer validates and
delegates; it must not calculate detours or manipulate provider payloads.

### Realtime tool

Person C must add a separate Realtime tool for the confirmed operation. The
instructions must clearly distinguish:

- searching;
- suggesting;
- selecting;
- asking for confirmation;
- confirmed rerouting;
- completed rerouting.

Suzanne must not say that a POI was added, that the route changed, or that a
new duration applies until the deterministic tool returns success.

Compact reroute output should contain only facts needed for speech, such as:

- destination;
- selected stop name and category;
- new total duration;
- new distance;
- mandatory charging summary;
- changed toll, border, or vignette facts when relevant.

Geometry, raw Places data, and full map details remain local to the frontend.

## Frontend behavior

### Map

Person A must make optional POI markers visibly distinct from:

- origin and destination markers;
- the route line;
- mandatory charging stops;
- any future selected/reroute waypoint.

Markers must have stable dimensions, sufficient contrast, and a z-index above
the route. Marker rendering must not depend on a category-specific hardcoded
coordinate.

A selected marker should:

- visually highlight;
- synchronize with the POI list;
- expose name, category, rating, amenity facts, and detour;
- offer selection for the voice confirmation flow;
- never reroute by click alone.

The map must render only the one or two backend-selected results. It must not
reintroduce a large unranked result set.

### List and state

`PoiResults` and map state must use the same result objects and IDs. The list
must show enough factual context to distinguish a cafe, fuel station with cafe,
rest area, attraction, or restaurant.

The assistant state must distinguish:

- active route;
- current POI suggestions;
- selected POI;
- reroute confirmation pending;
- reroute in progress;
- reroute success;
- reroute failure;
- Realtime session state.

Stopping voice must not reset the active route or current suggestions. A new
route and a new search have explicit state transitions. Abort and session
identity checks must prevent late requests from changing state after Stop or
route replacement.

### Error and empty states

The user must receive a useful state for:

- no active route;
- no POIs found in the route corridor;
- Google Places unavailable;
- invalid category;
- stale selected POI;
- reroute unavailable;
- reroute rejected because the selected POI is no longer valid;
- user stopped the session while a request was running.

Do not show raw HTTP messages, API keys, stack traces, or provider JSON.

## Team ownership

Ownership is explicit to prevent conflicting edits. Each person owns the files
listed below and the tests for the behavior they add. A person may propose a
change outside their ownership, but the owning person makes the edit after
review.

### Person A: Frontend HMI, map, and session lifecycle

**Primary responsibility:** What the driver sees and how the HMI behaves.

**Owns:**

- `frontend/src/App.tsx`;
- `frontend/src/features/map/components/RouteMap.tsx`;
- `frontend/src/features/assistant/components/PoiResults.tsx`;
- `frontend/src/features/assistant/components/AssistantStatus.tsx`;
  if present;
- frontend feature styles and map-specific components;
- frontend tests and browser acceptance tests;
- lifecycle/state sections of
  `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`.

**Delivers:**

- visible, distinct, selectable POI markers;
- synchronized list and marker selection;
- one-or-two-result presentation;
- POI persistence after Stop;
- clearing rules on new route and replacement search;
- stale-result protection at the UI boundary;
- loading, empty, error, and reroute-pending states;
- route replacement after successful reroute;
- accessible keyboard/focus behavior for list selection;
- mobile-safe layout and marker presentation.

**Must not:**

- invent POI data in the frontend;
- rank results independently of backend facts;
- reroute from a marker click without explicit confirmation;
- clear route or POI state merely because audio stopped;
- put provider API keys in browser code.

### Person B: Trip intelligence, POI policy, and rerouting

**Primary responsibility:** What is factually suitable for the journey.

**Owns:**

- `backend/app/services/trip/service.py`;
- `backend/app/services/trip/deterministic.py`;
- `backend/app/services/trip/fixture_providers.py`;
- `backend/app/services/recommendation/poi.py`;
- `backend/app/models/contracts.py`;
- backend trip and POI unit tests.

**Delivers:**

- route corridor filtering and distance-based relevance;
- result diversity and maximum result count;
- fuel, coffee, rest, toilets, charging, and service semantics;
- provider-neutral amenity representation;
- stale POI and selected-stop validation;
- confirmed POI waypoint rerouting;
- preservation of destination and mandatory charging stops;
- recalculation of duration, detour, tolls, borders, vignettes, and alerts;
- deterministic tie-breaking and testable thresholds.

**Must not:**

- add city-specific POIs to production code;
- parse Google HTTP payloads directly in domain services;
- silently change the active route during search;
- make partner status a prerequisite for a valid result;
- change Realtime wording without coordinating with Person C.

### Person C: Suzanne, tools, and conversation orchestration

**Primary responsibility:** What the driver means and what Suzanne says.

**Owns:**

- `backend/app/integrations/openai/realtime.py`;
- tool schemas and orchestration sections of
  `backend/app/api/assistant.py`;
- `frontend/src/services/realtimeAssistantApi.ts`;
- compact result construction and tool event sections of
  `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`;
- Realtime and API contract tests for tool behavior;
- relevant runtime documentation for voice flows.

**Delivers:**

- natural-language mapping for attractions, sightseeing, coffee, cafes,
  amenities, fuel, rest, and toilets;
- concise narration for one or two factual suggestions;
- explicit distinction between suggestion and reroute;
- voice confirmation before rerouting;
- compact search and reroute outputs;
- preservation of route context across follow-up requests;
- no invented availability, amenities, ratings, benefits, or route changes;
- stable user-facing error wording from structured backend errors.

**Must not:**

- calculate distances, duration, ranking, or amenities in prompt text;
- send geometry or raw Google responses to Realtime;
- claim a reroute before tool success;
- add provider-specific category names to public domain contracts without review.

### Person D: Google integration, configuration, and platform reliability

**Primary responsibility:** How the system connects to providers and runs safely.

**Owns:**

- `backend/app/integrations/places/google.py`;
- `backend/app/integrations/google_maps/routing.py`;
- `backend/app/main.py`;
- `backend/app/core/settings.py`;
- `backend/app/core/errors.py` when provider error mapping is involved;
- `.env.example`;
- `docker-compose.yml`;
- provider mocks and adapter integration tests;
- runtime and configuration documentation.

**Delivers:**

- distance-based full-route sampling;
- Google Places field masks and type classification;
- fuel, cafe, convenience, rest-area, toilet, and service mappings;
- bounded request count and configured radius;
- timeout and quota-safe behavior;
- stable provider error translation;
- dependency injection that chooses Google in configured production mode and
  explicit offline providers in tests/development;
- health/configuration checks without exposing secrets;
- mock-only automated provider tests;
- safe diagnostics containing category, sample count, result count, latency,
  and failure code, never API keys or raw payloads.

**Must not:**

- add live provider calls to CI tests;
- put Google-specific fields into domain services;
- embed Vienna, Budapest, or named commercial places in the adapter;
- log request headers, API keys, or complete provider responses;
- change shared contracts without review from Persons A, B, and C.

## Shared files and conflict protocol

The following files are shared and must have one designated editor per change:

- `backend/app/models/contracts.py`;
- `frontend/src/types/contracts.ts`;
- `backend/app/api/assistant.py`;
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`;
- `docs/api/contracts.md`;
- `docs/architecture/runtime.md`.

Protocol:

1. The person proposing a contract change writes the field-level proposal.
2. Person B reviews domain meaning and validation.
3. Person C reviews tool and compact-payload impact.
4. Person A reviews rendering and state impact.
5. Person D reviews serialization, configuration, provider, and failure impact.
6. One person makes the edit in one focused commit.
7. The owning tests are updated in the same change.
8. The integration branch runs the complete suite before the next shared edit.

Recommended merge order:

1. Contract and documentation proposal.
2. Provider adapters and mocked provider tests.
3. Deterministic POI policy and rerouting.
4. Realtime tools and compact payloads.
5. Frontend state and map presentation.
6. End-to-end integration fixes.

No person should reformat or reorganize another person's files while resolving a
functional change. Keep commits narrow and easy to review.

## Suggested implementation phases

### Phase 1: Contracts and behavior tests

Before changing provider code, agree on:

- public categories and amenity fields;
- maximum result count;
- route sampling and relevance semantics;
- POI identity and active-route validation;
- reroute request and response;
- Stop, new-route, and replacement-search lifecycle;
- error codes and empty-result behavior.

Add failing unit or contract tests for those decisions. Do not begin by adding
more fixture locations.

### Phase 2: Provider-backed route search

Implement Google route sampling, category mapping, amenity classification,
deduplication, route filtering, and bounded calls. Add mocked HTTP tests for
success, empty results, malformed results, timeout, quota failure, and route
versus destination searches.

Use a provider interface so tests can inject deterministic responses without
calling Google. The application should be able to run in offline mode using an
explicit test provider, but no offline fixture should be mistaken for live
Google data.

### Phase 3: Deterministic ranking and reroute service

Implement diversity-aware ranking and the maximum-two policy in the domain
service. Add explicit validation for selected POIs. Reuse the existing Google
Routes waypoint capability for the confirmed reroute and verify that mandatory
charging remains in the resulting route.

### Phase 4: Realtime tools

Add the explicit reroute tool and update instructions for category mapping,
confirmation, concise narration, and error behavior. Keep the compact payload
small. Tool outputs must contain facts, not explanations of provider internals.

### Phase 5: Frontend map and lifecycle

Add visible markers, synchronized selection, voice confirmation state, reroute
loading state, and route replacement. Ensure Stop preserves the last valid map
state and that aborted or stale calls cannot overwrite it.

### Phase 6: Integration and manual acceptance

Run mocked automated tests first, then test live Google behavior locally with a
configured key. Verify request count and provider responses without printing
secrets. Complete the acceptance scenarios below before calling Day 4 done.

## Acceptance scenarios

### Scenario 1: Route-wide attractions

Driver: `Can you tell me some cool stuff to see along the route?`

Expected:

- Suzanne calls an attraction search with `location=route`;
- Google-backed results are searched across the route corridor;
- results are not restricted to Vienna or Budapest;
- one or two diverse results are returned;
- the route geometry is unchanged;
- markers and list entries appear together;
- Suzanne describes only returned facts.

### Scenario 2: Coffee and petrol station amenities

Driver: `Can we find a coffee stop along the way?`

Expected:

- Suzanne uses the coffee category and route context;
- cafes and qualifying petrol/convenience stops can be returned;
- a fuel-only location without supporting amenity data is not described as a
  coffee stop;
- the result includes factual amenity information when available;
- no route change occurs.

### Scenario 3: Stop persistence

Driver:

1. Plans a route.
2. Requests attractions or coffee.
3. Presses Stop Suzanne.

Expected:

- microphone and Realtime close;
- the route remains visible;
- the suggested markers remain visible;
- no late response changes the map;
- a new session can continue from the existing displayed route according to the
  agreed product lifecycle.

### Scenario 4: Explicit POI reroute

Driver:

1. Requests a route POI.
2. Chooses one result by name or marker.
3. Confirms the proposed stop by voice.

Expected:

- selection alone does not change the route;
- confirmation triggers the reroute tool;
- the selected POI becomes a waypoint;
- destination and mandatory charging remain present;
- new geometry, duration, tolls, borders, and requirements are returned;
- the map updates only after successful backend confirmation;
- Suzanne reports only returned facts.

### Scenario 5: Generic destination change

Driver plans a different destination and then searches for route POIs.

Expected:

- no Vienna/Budapest-specific code is required;
- the route is searched from its actual geometry;
- previous-route POIs are not presented as current suggestions;
- provider failures and empty results are understandable.

### Scenario 6: Offline and provider failure

Run without a Google server key or with a mocked provider failure.

Expected:

- the application selects the documented offline/test provider or returns a
  clear configured-provider error;
- no fake live data is presented as Google data;
- no API key or stack trace is exposed;
- tests remain deterministic and do not call external APIs.

## Testing requirements

### Backend unit tests

Cover:

- route sampling over short and long geometries;
- bounded provider request count;
- route versus destination search context;
- Google place ID deduplication;
- route corridor distance filtering;
- category and Google-type mapping;
- fuel station eligibility for fuel, coffee, and rest;
- amenity claims based only on returned provider facts;
- maximum two results;
- spatial diversity;
- stable ranking and tie-breaking;
- stale POI rejection;
- selected POI validation;
- waypoint rerouting;
- preserved mandatory charging;
- recalculated durations, tolls, border crossings, and requirements;
- provider timeout, quota, malformed-response, and empty-result errors.

### Realtime and API tests

Cover:

- natural-language category mapping;
- required route/destination context;
- compact POI results;
- compact reroute results;
- no geometry or raw provider payload in Realtime output;
- explicit confirmation requirement;
- stable error envelopes;
- invalid category and stale POI behavior.

### Frontend tests

Cover:

- marker rendering and visual distinction;
- list/marker synchronization;
- one-or-two result presentation;
- selected POI state;
- confirmation-pending and reroute-in-progress states;
- route update after successful reroute;
- no route mutation during search;
- POI preservation after Stop;
- clearing on new route;
- late response isolation;
- empty and provider-error states;
- keyboard and screen-reader access to result selection.

### Required checks

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/backend -q
Set-Location frontend
npm run build
Set-Location ..
git diff --check
git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- .
```

Automated tests must never depend on live Google or OpenAI calls. Manual live
acceptance may use configured local credentials, but credentials must remain in
`.env` and never be committed or printed.

## Definition of done

Day 4 is complete only when:

- live Google-backed POI search covers the route corridor rather than only city
  endpoints;
- petrol/fuel stations are handled with truthful coffee/rest amenity rules;
- no production provider contains a hardcoded list of demo businesses or route
  coordinates;
- the backend returns at most two diverse suggestions;
- suggestions are visible and selectable on the map;
- Stop preserves route and POI map state;
- rerouting requires explicit driver confirmation;
- confirmed rerouting preserves destination and mandatory charging;
- route facts are recalculated deterministically;
- Realtime receives compact facts only;
- provider failures, stale requests, and empty results are handled clearly;
- ownership and shared-file boundaries are respected;
- backend tests, frontend build, static checks, and manual acceptance pass.

Do not call the project complete because a Google request returned HTTP 200.
The full route behavior, frontend rendering, session lifecycle, and explicit
reroute flow must also be verified.

## Deferred work

The following remain intentionally deferred unless the team explicitly expands
Day 4 after the core acceptance bar passes:

- real payment or booking;
- production authentication and user accounts;
- remote database or persistent trip history;
- Europe-wide POI coverage guarantees;
- autonomous rerouting without driver confirmation;
- multi-day itinerary optimization;
- production traffic prediction;
- 3D cockpit presentation;
- unrestricted background polling of vehicle or provider data.

Simulated `pay_toll` and `book_poi` contracts may be designed during Day 4, but
implementation should happen only after provider-backed search, POI selection,
and rerouting are stable and tested.
