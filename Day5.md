# Day 5: Partner Network, Route-Scoped Discovery, and HMI Polish

## Purpose

Day 5 is a polish and trust day. The goal is to make the existing Day 4
experience feel coherent, useful, and presentation-ready without weakening the
deterministic route and provider boundaries.

Day 5 delivers four connected improvements:

1. Expand partners from individual locations into brand-wide partner networks.
2. Make route attraction searches genuinely route-scoped while keeping
   destination searches available on request.
3. Let Suzanne search for amenities around a selected charging stop and show
   those amenities on the map.
4. Polish the frontend HMI, map startup state, marker language, and Realtime
   connection experience.

The core interaction should become:

```text
Driver plans a route
    -> Suzanne identifies a charging stop
    -> driver asks about amenities near that stop
    -> deterministic service searches a 500 m provider radius
    -> Suzanne reports only returned facts
    -> frontend zooms to the charging stop and shows nearby markers
```

Day 5 must not turn partner data into fake provider data. A partner brand can
provide optional enrichment for a real provider result, but partner status must
never create a location that Google Places did not return.

## Product outcomes

At the end of Day 5:

- Ionity, ChargePoint, TEA, and other supported brands are represented as
  brand-level partner networks rather than one-off location records.
- Existing and newly discovered locations can receive optional brand partner
  enrichment when the provider returns a matching brand.
- A route search for attractions excludes the first and last 10 km of the
  route by default.
- A destination search remains available when the driver explicitly asks for
  attractions or POIs near the destination.
- Route searches use a named 5-10 km corridor policy and bounded provider
  requests.
- Suzanne understands requests such as:
  - `What can I see along the route?`
  - `Are there any amenities near that charging station?`
  - `Is ChargePoint Parndorf near anything interesting?`
  - `Find coffee and food around the charging stop.`
- Charging-stop amenity searches use a 500 m radius around the selected stop.
- Nearby results are shown with factual categories and amenities.
- The frontend opens directly in a driving-oriented origin view before a route
  exists.
- The pre-route map shows a tilted origin view and a blue origin marker.
- A planned route switches to an appropriate bird's-eye route view.
- Charging, coffee, food, rest, attraction, hotel, and service markers are
  visually distinct and consistent.
- Starting Suzanne feels responsive, with visible connection progress and no
  unnecessary delay caused by frontend sequencing.
- No two people edit the same implementation file.

## Non-negotiable architecture rules

- Google provider payloads never enter Realtime messages or browser state.
- Deterministic services decide route scope, radius, ranking, matching, and
  factual amenity claims.
- Suzanne interprets structured facts and narrates them; she does not calculate
  distance, radius, route position, or partner matching in prompt text.
- Searching is read-only. Searching near a charger must not silently add a
  waypoint or change the route.
- Selecting a result does not reroute. Rerouting still requires explicit
  confirmation.
- Partner brand matching is optional enrichment and never a safety decision.
- Automated tests never call live Google or OpenAI services.
- Live provider acceptance is a manual local test using credentials kept in
  `.env`.
- Every numeric policy is named configuration or a named constant with tests.

## Ownership model: no shared implementation files

Each file has exactly one owner for Day 5. A person may review another
person's work, but must not edit that person's file. Do not resolve conflicts by
editing another person's owned file.

### Person A: HMI, map, markers, and visual polish

**Owns only:**

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/features/map/components/RouteMap.tsx`
- `frontend/src/features/map/components/MapShell.tsx` if created
- `frontend/src/features/map/components/MapMarkers.tsx` if created
- `frontend/src/features/assistant/components/AssistantStatus.tsx`
- `frontend/src/features/assistant/components/PoiResults.tsx`
- `frontend/src/features/trip/components/RouteSummary.tsx`
- `frontend/src/assets/**`
- `tests/frontend/**`
- `tests/e2e/frontend/**`

**Delivers:**

- pre-route driving map view rendered on initial page load;
- blue origin marker with no route line before planning;
- tilted map camera before a route exists;
- bird's-eye camera and bounds fitting after route planning;
- no full map teardown when assistant text, POIs, or selection changes;
- distinct markers for origin, destination, mandatory charging, coffee, food,
  rest, attractions, hotels, service, and selected stops;
- stable marker dimensions, labels, contrast, and z-index;
- zoom-to-charging-stop behavior when charging amenities are displayed;
- synchronized amenity list and map markers;
- polished loading, empty, error, and no-route states;
- responsive layout and keyboard-accessible POI selection;
- manual map refreshes only when route geometry or camera intent changes.

**Must not edit:** backend files, Realtime tool schemas, contracts, API bridge,
Google adapters, partner JSON, or trip policy.

### Person B: deterministic trip and amenity policy

**Owns only:**

- `backend/app/services/trip/service.py`
- `backend/app/services/trip/deterministic.py`
- `backend/app/services/recommendation/poi.py`
- `backend/app/services/trip/fixture_providers.py`
- `backend/app/core/fixture_repository.py` only when partner loading requires it
- `tests/backend/unit/test_route_service.py`
- `tests/backend/unit/test_day3_deterministic.py`
- `tests/backend/unit/test_day5_trip_policy.py` if created

**Delivers:**

- named route corridor policy, defaulting to 5-10 km according to settings;
- exclusion of the first and last 10 km for route attraction searches;
- explicit distinction between `route`, `stop`, and `destination` searches;
- 500 m charging-stop amenity radius policy;
- validation that amenity searches require a current selected stop;
- route-safe ranking, diversity, and maximum-result rules;
- brand enrichment application after provider results exist;
- partner-first charging selection among reachable candidates, then non-partner
  fallback;
- charging-time calculation from vehicle energy demand and provider charger
  power when available;
- no route mutation during amenity search;
- stale route, stale stop, and stale search rejection;
- tests for origin/destination exclusion and charging-stop proximity.

**Must not edit:** Google HTTP parsing, partner fixture content, frontend files,
Realtime instructions, API endpoint wiring, or public contract definitions.

### Person C: Suzanne conversation and tool orchestration

**Owns only:**

- `backend/app/integrations/openai/realtime.py`
- `backend/app/api/assistant.py`
- `frontend/src/services/realtimeAssistantApi.ts`
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`
- `tests/backend/integration/test_realtime_api.py`
- `tests/backend/unit/test_openai_realtime.py`
- `docs/api/day5-voice-flows.md`

**Delivers:**

- natural-language mapping for route attractions versus destination attractions;
- recognition of `near the charging station`, `around that charger`, and
  `amenities nearby`;
- a dedicated `search_stop_amenities` tool, separate from route POI search;
- compact amenity results containing only names, categories, factual amenities,
  distance/radius facts, and the selected charging stop name;
- explicit distinction between searching near a stop and adding a stop;
- concise truthful responses such as:
  `Yes. ChargePoint Parndorf is near a shopping complex with food and coffee.`
- frontend state for amenity-search loading, success, empty, stale, and failure;
- latency instrumentation around session creation and tool calls;
- a visible connection-progress state that does not claim readiness too early;
- no invented availability, opening hours, facilities, ratings, or partner
  benefits.

**Must not edit:** provider adapters, deterministic ranking, partner JSON,
frontend visual components, map camera implementation, or public contract files.

### Person D: providers, partner data, configuration, and reliability

**Owns only:**

- `backend/app/integrations/places/google.py`
- `backend/app/integrations/places/provider.py`
- `backend/app/integrations/google_maps/routing.py`
- `backend/app/main.py`
- `backend/app/core/settings.py`
- `backend/app/core/errors.py`
- `.env.example`
- `docker-compose.yml`
- `data/partners/partners.json`
- `data/places/places.json` only for explicit offline fixtures
- `tests/backend/unit/test_google_integrations.py`
- `tests/backend/unit/test_day5_google_places.py` if created
- `docs/architecture/runtime.md`
- `docs/configuration/day5-providers.md`

**Delivers:**

- Google Search Along Route or the supported Google Places route-corridor
  operation, behind a provider-neutral adapter;
- a named configurable route search radius between 5 and 10 km;
- a named 500 m nearby-stop search radius;
- exclusion-aware request strategy that avoids treating origin and destination
  city results as route attractions;
- explicit destination-centered searches when requested;
- provider field masks containing only fields used by the domain;
- brand/type parsing for Ionity, ChargePoint, TEA, OMV, Petrom, MOL, hotels,
  restaurants, cafes, convenience stores, and service locations;
- provider-neutral amenity facts and optional provider brand identity;
- timeout, quota, malformed-response, and bounded-request handling;
- safe provider diagnostics without keys or raw responses;
- configuration that clearly selects Google or offline mode.

**Must not edit:** trip ranking or charging policy, Realtime prompts/tools,
frontend components, or contract models.

## File ownership matrix

| File or area | Owner | Other people may review | Other people may edit |
|---|---|---|---|
| `frontend/src/App.tsx` | Person A | A/B/C/D | No |
| `frontend/src/index.css` | Person A | A/B/C/D | No |
| `frontend/src/features/map/**` | Person A | A/B/C/D | No |
| `frontend/src/features/assistant/components/**` | Person A | A/B/C/D | No |
| `frontend/src/features/trip/components/**` | Person A | A/B/C/D | No |
| `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts` | Person C | A/B/D | No |
| `frontend/src/services/realtimeAssistantApi.ts` | Person C | A/B/D | No |
| `frontend/src/types/contracts.ts` | Person C | A/B/D | No |
| `backend/app/models/contracts.py` | Person C | A/B/D | No |
| `backend/app/api/assistant.py` | Person C | A/B/D | No |
| `backend/app/integrations/openai/realtime.py` | Person C | A/B/D | No |
| `backend/app/services/trip/**` | Person B | A/C/D | No |
| `backend/app/services/recommendation/**` | Person B | A/C/D | No |
| `backend/app/integrations/places/**` | Person D | A/B/C | No |
| `backend/app/integrations/google_maps/**` | Person D | A/B/C | No |
| `backend/app/main.py` | Person D | A/B/C | No |
| `backend/app/core/settings.py` | Person D | A/B/C | No |
| `data/partners/partners.json` | Person D | A/B/C | No |
| `data/places/places.json` | Person D | A/B/C | No |
| `tests/backend/unit/test_route_service.py` | Person B | A/C/D | No |
| `tests/backend/unit/test_google_integrations.py` | Person D | A/B/C | No |
| `tests/backend/integration/test_realtime_api.py` | Person C | A/B/D | No |
| `tests/frontend/**` | Person A | B/C/D | No |
| `tests/e2e/frontend/**` | Person A | B/C/D | No |
| `docs/api/day5-voice-flows.md` | Person C | A/B/D | No |
| `docs/architecture/runtime.md` | Person D | A/B/C | No |
| `.env.example` | Person D | A/B/C | No |

No Day 5 task may assign the same file to two people.

## Parallel delivery protocol without shared-file edits

All four people work in parallel from the same Day 4 integration baseline.
No person waits for another person to finish implementation. Coordination
happens through frozen proposals, compatibility notes, and owned-file commits,
not through shared working files.

### Kickoff: one shared baseline, four independent branches

The team lead creates the integration branch from the latest validated Day 4
commit. Each person branches from that exact commit:

```text
integration/day5
|-- person-a/day5-hmi
|-- person-b/day5-policy
|-- person-c/day5-suzanne
`-- person-d/day5-providers
```

All four branches may be active at the same time. Each person owns and edits
only the files listed in the ownership matrix. Before coding, Person C posts a
contract proposal containing the exact request/response examples. This is a
read-only coordination artifact for the other three people; it is not a reason
for anyone to wait.

### Parallel work rules

1. Person A, B, C, and D begin their assigned slices immediately from the same
  baseline.
2. Each person commits only files they own.
3. Each person writes tests in their owned test area and runs those tests
  independently.
4. Each person publishes a short branch note containing changed files,
  contract assumptions, test command, and result.
5. No person edits, formats, or fixes another person's files.
6. A needed change outside a person's ownership becomes a proposal for the
  owner; the owner applies it in their own branch.
7. Shared contract files are edited only by Person C. Other people code against
  the frozen proposal and may use local type stubs or test factories in their
  own owned test files until the integration merge.
8. Backward-compatible additions are preferred. Existing Day 4 fields and
  tools must continue to work while Day 5 fields are introduced.
9. No branch rebases or squashes contributor work when authorship matters.

### Integration assembly

When each branch is ready, the team lead merges the four branches into
`integration/day5` in any order because their owned implementation files do
not overlap. A merge is not permission for one contributor to repair another
contributor's files. If a conflict appears, the affected file returns to its
owner for resolution in a follow-up commit.

The team lead runs the complete validation after all four branches are merged.
Person A is the final Day 5 verifier and owns the acceptance decision:

- Person A checks every item in the Day 5 definition of done;
- Person A runs the full backend, frontend, static, and manual acceptance
  checklist;
- Person A records any missing requirement as a blocking integration issue;
- the owner of the affected file fixes it on their branch without blocking the
  other contributors' completed work;
- the team lead merges the fix and repeats the relevant checks;
- only Person A may approve the final `integration/day5` state for `main`.

This makes the work parallel while keeping one accountable final verifier.

### Person A as team lead

Person A is the Day 5 integration lead. This does not make Person A a
dependency for the other three workstreams. Person A codes their HMI slice in
parallel and performs the final product verification after assembly.

Person A is responsible for:

- confirming that every Day 5 requirement has an implemented owner;
- confirming that every changed file has exactly one owner;
- checking that provider data, deterministic policy, Suzanne narration, and
  frontend rendering agree on the same contract;
- reviewing all four branch handoff notes;
- approving or rejecting the integrated branch against the definition of done;
- authorizing the final merge or fast-forward of `integration/day5` to `main`;
- pushing to `main` only after the complete validation gate passes.

The final GitHub history must retain all four contributor branch tips and
merge commits. Do not squash, rebase, or force-push the integration history
when contributor attribution matters.

### Required branch handoff note

Every person must provide this in their pull request or branch description:

```text
Owned files:
Day 5 requirements covered:
Contract assumptions:
Tests run:
Manual checks still needed:
Known limitations:
```

The integration branch must not be pushed to `main` until all four handoff
notes are present and Person A has checked them against the roadmap.

### Integration command gate

From the repository root, Person A runs:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/backend -q
Set-Location frontend
npm run build
Set-Location ..
git diff --check
git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- .
```

The final manual gate must include the route attraction, destination
attraction, charging-stop amenity, origin-only map, marker, Stop persistence,
and Realtime latency scenarios below.

## Partner network design

### Brand-level partner records

`data/partners/partners.json` must describe partner networks and benefits by
brand, not pretend that one coordinate represents every location.

Recommended shape:

```json
{
  "id": "partner-ionity",
  "brand": "IONITY",
  "categories": ["charging"],
  "providerBrands": ["IONITY"],
  "benefit": "Ultra-fast charging partner rate",
  "amenities": ["charging"],
  "enabled": true
}
```

The exact schema is owned by Person C and implemented in coordination with
Person D's fixture loading. Existing location-specific records should not be
silently interpreted as a whole brand.

Initial brand groups:

- Charging: IONITY, ChargePoint, TEA.
- Fuel and convenience: OMV, Petrom, MOL, and verified gas-station brands.
- General stop amenities: convenience, coffee, snacks, toilets, rest, and
  service-area providers where provider data supports the claim.
- Hotels: supported hotel groups returned by provider data.
- Restaurants: supported restaurant groups returned by provider data.
- Attractions and venues: only when a real provider result has a matching
  partner identity.

Brand matching rules:

- normalize case, punctuation, and common provider prefixes;
- match provider brand identity before display-name substring guessing;
- keep location coordinates from Google Places, never from the partner record;
- attach the partner benefit only after a provider result matches the brand;
- do not mark an entire category as partnered because one location matched;
- a vignette requirement can exist without a partner benefit.

## Route attraction search

### Route request

For a request such as:

> Can you tell me something cool I can see on the route?

Suzanne must issue a route-scoped attraction search with:

- location: `route`;
- category: `attraction`;
- route corridor radius: configurable, default 7.5 km;
- origin exclusion radius: 10 km;
- destination exclusion radius: 10 km;
- bounded route sample/request count;
- maximum two diverse results after deterministic ranking.

The origin and destination exclusions apply to route searches only. They must
not affect an explicit request such as:

- `What can I see in Budapest?`
- `Find attractions near my destination.`
- `Show me something interesting in Berlin.`

Destination searches use a destination-centered provider request and may return
places in the destination city.

### Ranking and truthfulness

Rank attraction candidates by:

- route corridor distance;
- estimated detour;
- position along the route;
- rating when available;
- preference match;
- geographic diversity;
- stable provider ID.

Suzanne may say only that a returned attraction is near the route or near the
destination. She must not claim that a place is open, free, family-friendly,
accessible, scenic, or available unless the provider returned that fact.

## Amenities near a charging stop

### User flow

Example:

```text
Suzanne: I found ChargePoint Parndorf, a charging stop with a 25-minute
estimated charge.
Driver: Are there any amenities nearby for me to spend my time at?
Suzanne: I found a shopping complex 350 metres away with food and coffee.
```

### Deterministic operation

Add a dedicated provider-neutral operation, for example:

`POST /api/assistant/realtime/tools/search-stop-amenities`

The request contains compact validated context only:

```json
{
  "stopId": "place-chargepoint-parndorf",
  "routeId": "active-route-id",
  "searchId": "active-search-id",
  "categories": ["food", "coffee", "rest", "shopping"]
}
```

The backend must:

1. validate that the stop belongs to the active route or current search;
2. validate that the stop is a charging stop or selected route stop;
3. search the provider with a 500 m radius centered on the stop coordinates;
4. deduplicate and rank nearby results;
5. return no more than four useful diverse amenities;
6. preserve provider names, categories, ratings, and factual amenity labels;
7. never mutate route geometry or add a waypoint;
8. reject stale stop and stale route context safely.

### Frontend behavior

When amenity results arrive:

- zoom the map to the selected charging stop and nearby results;
- retain the full route in application state;
- show a selected-stop halo or focus marker;
- add category-specific nearby markers;
- synchronize the nearby-amenity list with map selection;
- provide a clear way to return to the full-route view;
- do not replace the route or interpret amenity search as a reroute.

### Suzanne behavior

Suzanne must:

- recognize references such as `that charger`, `nearby`, and `spend my time`;
- call the dedicated amenity tool only after a charging stop is known;
- report distance using deterministic returned facts;
- summarize grouped amenities without inventing a shopping complex;
- say `I found food and coffee nearby` only when those categories were returned;
- say `I found a shopping complex` only when provider data identifies one;
- ask whether the driver wants a more specific category if no amenities exist.

## Frontend polish

### Initial driving view

On first load, before route planning:

- render the map immediately when the browser key is available;
- center it on the configured vehicle origin;
- use a restrained tilted driving view;
- show one blue origin marker;
- show no route line, destination marker, POI markers, or fake route data;
- show a calm empty-state panel rather than a blank page.

After route planning:

- switch to bird's-eye view;
- fit the full route bounds;
- show origin, destination, mandatory stops, selected stops, and optional POIs;
- preserve map instance while suggestions or assistant narration changes;
- use semantic marker icons and stable dimensions.

If Google Maps is unavailable, show a useful local state without inventing a
route or silently substituting fake map geometry.

### Marker vocabulary

Use a consistent visual language:

- origin: blue location marker;
- destination: white or deep-blue destination marker;
- charging: electric/bolt marker;
- coffee: cup marker;
- food/restaurant: fork-and-knife marker;
- rest/toilets: pause or facility marker;
- attraction: camera/star marker;
- hotel: bed marker;
- service/fuel: wrench or fuel marker;
- selected result: highlighted marker plus focus ring;
- partner enrichment: small secondary partner badge, never the primary safety
  signal.

## Realtime latency reduction

Measure before optimizing. Person C must record timestamps for:

- Start button pressed;
- microphone permission requested/granted;
- Realtime session request started/completed;
- peer connection created;
- data channel opened;
- remote description applied;
- assistant ready.

Candidate improvements:

- request the ephemeral Realtime session and microphone permission in parallel;
- create the peer connection immediately after both are available;
- avoid waiting for unrelated UI or audio work;
- reuse the existing audio element setup where safe;
- show `Connecting Suzanne...` immediately after Start;
- show `Listening` only after the data channel is open and the session is
  configured;
- abort cleanly on Stop;
- do not reduce security or expose the long-lived OpenAI API key.

The target is a measurable reduction in perceived connection delay, not a
hardcoded promise that connection always takes a particular number of seconds.

## Parallel implementation workstreams

The following four workstreams start at the same time. They are intentionally
independent and may use proposal documents, local test factories, and mocked
responses to stand in for work being completed in another branch.

### Workstream A: HMI and presentation

Person A works in parallel on the initial map, bird's-eye transition, marker
vocabulary, amenity focus mode, responsive layout, accessibility, and frontend
tests. Person A does not wait for live backend responses; mocked contract
fixtures are sufficient during this workstream.

### Workstream B: Deterministic policy

Person B works in parallel on route exclusions, 500 m stop-radius policy,
stale-context validation, ranking, diversity, partner enrichment behavior, and
backend policy tests. Person B uses the frozen proposal examples from Person C
and provider-neutral factories rather than editing provider or contract files.

### Workstream C: Suzanne and contracts

Person C works in parallel on the contract proposal, nearby amenity tool,
route-versus-destination intent mapping, compact facts, latency timestamps,
Realtime instructions, API bridge, and tool tests. Person C is the sole editor
of public contract files and conversation orchestration files.

### Workstream D: Providers and partner networks

Person D works in parallel on brand-level partner fixtures, Google route and
nearby searches, provider brand parsing, field masks, configuration, provider
mocks, and reliability documentation. Person D uses Person C's proposal as the
target shape but does not wait for Person C's implementation branch.

### Final integration and verification

After the four independent branches are complete, the team lead merges all
four into `integration/day5`. Person A then verifies the assembled branch
against every Day 5 requirement and owns the go/no-go decision for `main`.

The contributors do not merge one another's branches or wait in a dependency
chain. The only serialized activity is final assembly, verification, and the
push to `main`, because those steps require the complete product rather than a
partial workstream.

## Testing requirements

### Backend

- brand matching is case/punctuation/provider-name tolerant;
- location coordinates always come from provider results;
- partner enrichment is optional and does not affect route safety;
- route attraction searches exclude origin and destination radii;
- destination attraction searches can return destination-city results;
- route corridor is between 5 and 10 km by configuration;
- nearby amenity searches use exactly the configured 500 m radius;
- nearby amenity searches require active stop context;
- stale stop and route IDs are rejected;
- result count and diversity policies hold;
- no raw provider payload enters public responses;
- charging partner preference and non-partner fallback remain correct;
- charging duration uses provider power when available and a named fallback
  otherwise;
- provider timeout, quota, malformed-response, and empty-result errors map
  consistently.

### Frontend

- initial map renders with origin-only driving view;
- no fake route is shown before planning;
- route planning switches to bird's-eye view;
- map instance is not recreated for POI or narration updates;
- marker categories are visually distinct;
- selected charging stop zooms to nearby amenities;
- nearby markers and list remain synchronized;
- return-to-route view restores the full route;
- Stop preserves route and nearby amenity state;
- stale responses cannot overwrite current map state;
- connection progress states are accurate;
- keyboard, focus, and screen-reader behavior works for results.

### Manual acceptance scenarios

1. Open the site with no route and verify the tilted origin-only driving view.
2. Start Suzanne and verify connection progress feels immediate.
3. Ask for Vienna to Budapest fastest.
4. Verify a reachable charging stop, partner enrichment when applicable, and
   estimated charging duration.
5. Ask: `Can you tell me something cool I can see on the route?`
6. Verify results are not simply in Vienna or Budapest and are within the
   configured route corridor.
7. Ask: `What can I see in Budapest?`
8. Verify destination attractions are allowed.
9. Ask: `Are there any amenities nearby for me to spend my time at?`
10. Verify Suzanne searches within 500 m of the selected charger.
11. Verify the map zooms to that charger and displays accurate food, coffee,
    rest, shopping, or other returned amenity markers.
12. Verify the route itself does not change during amenity search.
13. Press Stop and verify route, selected charger, and nearby amenities remain.
14. Start a new route and verify old suggestions do not leak into the new
    route.

## Definition of done

Day 5 is complete when:

- partner data is brand-wide and location coordinates remain provider-owned;
- Ionity, ChargePoint, TEA, OMV, Petrom, MOL, hotel, and restaurant partner
  categories are represented without fake location records;
- route attraction searches use a configurable 5-10 km corridor;
- route attraction searches exclude the first and last 10 km;
- destination attraction searches remain available explicitly;
- charging-stop amenity search uses a 500 m provider radius;
- Suzanne reports only factual returned amenities;
- nearby amenities appear as accurate map markers and synchronized list items;
- the map opens in an origin-only driving state and transitions to route view;
- marker semantics are visually clear;
- Realtime startup latency is measured and improved where feasible;
- no two contributors edit the same implementation file;
- backend tests, frontend build, static checks, and manual acceptance pass.

## Deferred beyond Day 5

- real payments, reservations, or loyalty-account linking;
- background live vehicle polling;
- production user accounts and trip history;
- autonomous rerouting;
- guaranteed Europe-wide POI coverage;
- exact opening-hours or real-time availability claims unless supported by the
  selected provider fields;
- full 3D cockpit mode until the 2D HMI is stable.
