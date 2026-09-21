# Day 8: Brand-Wide Partner Intelligence, Trip Memory, and Multi-Stop Charging

## Purpose

Day 8 turns partner data from passive location metadata into a deterministic,
brand-wide capability that Suzanne can proactively present during route
planning. It also closes three route-conversation defects:

- Suzanne repeats charging or vignette requirements after they are completed.
- Costs are spoken with duplicated or incorrect currency wording, such as
  "16 dollars and 50 cents euros".
- Routes requiring two or more charging stops do not consistently produce or
  confirm a safe sequence of stops.

The result must remain voice-first, truthful, deterministic, and suitable for
the existing infotainment demo. Suzanne may suggest a partner or amenity
without being asked, but adding a waypoint, purchasing a vignette, or booking
anything still requires the existing explicit authorization rules.

## Product outcomes

By the end of Day 8:

- A returned charging, hotel, restaurant, coffee, or amenity result is matched
  against a brand-wide partner record by normalized brand/provider identity.
- A matching brand exposes its configured benefit at every eligible location;
  the system does not require a separate partner record for every station,
  hotel, or restaurant.
- Suzanne proactively mentions the most relevant verified partner benefit after
  route planning or an amenity search.
- Suzanne never claims a benefit when the brand is ambiguous, disabled, outside
  the configured category, or missing an eligible offer.
- A route with a required charging stop returns a safe ordered charging plan,
  including every stop required by initial range and post-charge range.
- Charging confirmation applies the complete planned sequence, not only the
  first stop, and returns the charging facts for every confirmed stop.
- A completed charging confirmation and a purchased vignette are remembered
  for the active route session and are not requested again.
- Every spoken monetary amount uses one clear EUR format, for example
  "16.50 euros" or "16 euros and 50 cents", never both formats together.
- The full backend, frontend, browser, and documentation validation gates pass.

## Scope and safety boundary

Day 8 adds deterministic partner matching, proactive recommendations, route
session memory, currency wording, and multi-stop charging reliability. It does
not add:

- real partner APIs, real discounts, real payments, or production loyalty
  accounts;
- permanent driver profiles or cross-session personalization;
- automatic route changes without spoken confirmation;
- invented availability, opening hours, prices, or commercial eligibility;
- a separate partner microservice or database.

All partner benefits in local fixtures are simulated demo benefits unless a
future integration provides authoritative commercial data. The voice layer must
not present fixture benefits as real-world guarantees.

## Core interaction flows

### Route planning with a charging partner

1. The driver requests a route.
2. The routing service calculates the route and determines whether charging is
   required.
3. The charging provider returns suitable candidates.
4. The deterministic policy selects an ordered safe sequence using current
   range, safety buffer, and maximum charged range.
5. Each returned candidate is matched against the brand-wide partner catalog.
6. The route response includes a compact, read-only partner opportunity.
7. Suzanne says, for example:

   > You will need to charge once. The best suitable option is a Shell station,
   > which offers 10% off charging costs through our partner program. Shall I
   > add it to the route?

8. The route is not mutated until the driver confirms charging.
9. Confirmation adds the complete planned charging sequence and returns the
   selected partner benefits and nearby amenities.

### Charging station with a nearby amenity partner

If a selected Shell station has a nearby McDonald's result with a configured
brand-wide benefit, Suzanne may say:

> There is a McDonald's within 500 metres offering a free drink with every
> order. It is nearby, but I have not added it to the route.

If the McDonald's result is merely nearby and has no configured benefit,
Suzanne must say only:

> There is a McDonald's nearby if you would like a quick stop.

A nearby place must never inherit a benefit from the charging station unless
the partner data explicitly defines that relationship.

### Hotel or restaurant opportunity

After route planning, the opportunity evaluator may return one or two relevant
destination or route alternatives. Suzanne can proactively say:

> I found a partner hotel near Budapest with free breakfast. It adds three
> minutes to the route. Would you like to compare it?

This is a suggestion only. Selecting, rerouting through, or booking the result
uses the existing explicit confirmation and booking rules.

## Partner catalog contract

`data/partners/partners.json` becomes a catalog of brand-wide partner offers,
with optional location-specific records. The catalog must support these two
forms:

### Brand-wide record

```json
{
  "id": "brand-mcdonalds",
  "kind": "brand",
  "brand": "McDonald's",
  "brandAliases": ["McDonalds", "McDonald's", "MCDONALDS"],
  "categories": ["restaurant", "coffee", "food"],
  "providerBrands": ["McDonald's", "McDonalds"],
  "benefit": "Free drink with every order",
  "benefitScope": "brand-wide",
  "eligibleLocations": "all-matched-locations",
  "amenities": ["food", "coffee", "toilets"],
  "enabled": true
}
```

### Location-specific override

```json
{
  "id": "shell-vienna-budapest-001",
  "kind": "location",
  "brand": "Shell",
  "name": "Shell Hegyeshalom",
  "categories": ["charging", "rest", "coffee"],
  "providerBrands": ["Shell", "Shell Recharge"],
  "coords": [17.15, 47.91],
  "benefit": null,
  "benefitScope": "location",
  "amenities": ["charging", "coffee", "rest"],
  "enabled": true,
  "detourMinutes": 2,
  "chargingDurationMinutes": 28
}
```

The implementation may preserve backward-compatible fields while migrating,
but the following rules are mandatory:

- `kind: "brand"` means the benefit applies to every safely matched eligible
  result for that brand.
- `kind: "location"` means the benefit applies only to that exact location.
- `benefitScope` must be explicit: `brand-wide`, `location`, or `none`.
- A brand record may define aliases and provider brand names, but matching must
  use normalized exact identity, not broad fuzzy similarity.
- A brand-wide benefit must define applicable categories. A restaurant offer
  must not appear on a hotel or charging result.
- A benefit must be concise, concrete, and directly speakable.
- Disabled, expired, or missing-benefit records must not produce a commercial
  claim.
- Partner identity and benefit provenance must be available to the backend and
  compact voice facts.
- Location records must still contain valid coordinates when they represent a
  direct stop. Brand records do not need coordinates.

### Catalog coverage target

Person B must build a broad simulated catalog covering the existing demo
corridors and destination searches. The minimum target is:

- charging brands: Shell, MOL Plugee, IONITY, ChargePoint, TEA, and at least
  two additional charging networks;
- restaurant and coffee brands: McDonald's, KFC, Starbucks, Subway, and at
  least four additional brands;
- hotel brands: at least ten brands distributed across Vienna, Budapest,
  Bratislava, Győr, Berlin, Brno, and relevant corridor destinations;
- at least three distinct benefit types per category;
- aliases for provider naming variations such as `MOL Plugee`, `MOL Plugee
  Charger`, `Shell Recharge`, and localized punctuation/casing;
- enough location fixtures for the Vienna-Budapest and Vienna-Berlin offline
  demonstrations to return meaningful results.

The catalog must not pretend that a real-world commercial arrangement exists.
Fixture benefits are explicitly demo partner benefits and should be labeled as
such in documentation and tests.

## Role split and file ownership

No implementation file may have two owners. Reviews are encouraged, but edits
go to the owner listed below. Shared contract changes must be agreed before
dependent branches implement against them.

### Person A: partner presentation and browser acceptance

**Owns only:**

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/features/map/**`
- `frontend/src/features/assistant/components/**`
- `frontend/src/features/trip/components/**`
- `frontend/src/features/commerce/components/**`
- `tests/frontend/**`
- `tests/e2e/frontend/**`

**Delivers:**

- Partner brand, benefit, scope, and verification state are visible wherever
  structured partner facts exist.
- Multiple charging stops render in route order with clear progress/state.
- The UI distinguishes a recommendation from an added waypoint and a completed
  purchase.
- Cost cards render EUR values without duplicated currency wording.
- Browser acceptance covers proactive partner narration, accepted/rejected
  charging plans, repeated route questions, vignette memory, and two-stop
  routes.

**Must not edit:** backend services, partner fixtures, shared contracts,
Realtime instructions, provider adapters, or wallet logic.

### Person B: partner catalog, trip policy, and route session state

**Owns only:**

- `backend/app/services/trip/**`
- `backend/app/services/recommendation/**`
- `backend/app/services/wallet/**`
- `backend/app/services/commerce/**`
- `data/partners/partners.json`
- `data/commerce/**`
- `tests/backend/unit/test_route_service.py`
- `tests/backend/unit/test_day5_trip_policy.py`
- `tests/backend/unit/test_day6_commerce.py`
- `tests/backend/unit/test_day6_wallet.py`
- new `tests/backend/unit/test_day8_partner_policy.py`
- new `tests/backend/unit/test_day8_multi_stop_charging.py`
- new `tests/backend/unit/test_day8_route_memory.py`

**Delivers:**

- The brand-wide catalog and migration-compatible schema described above.
- Deterministic exact brand matching with aliases and provider brand names.
- A bounded opportunity evaluator that ranks partner suggestions by route
  relevance, safety, requested priority, detour, rating, and benefit
  relevance. Partner status is not allowed to override an unsafe or unsuitable
  charging stop.
- Charging selection as an ordered iterative algorithm:
  - begin with current estimated range;
  - choose a reachable compatible stop before the safety boundary;
  - after charging, use `max_charged_range_km` as the next range ceiling;
  - subtract the distance to the next stop and continue until the destination
    is reachable;
  - reject loops, duplicate stops, unreachable transitions, and incomplete
    sequences;
  - preserve route order and deterministic tie-breaking.
- Charging confirmation that applies all pending stops in order and returns
  per-stop facts and amenities without dropping later stops.
- Active route session state containing at least:
  - `charging_plan_confirmed`;
  - confirmed charging stop IDs;
  - purchased vignette requirement IDs;
  - route ID and session generation;
  - completed partner opportunity IDs where needed to avoid repetition.
- Idempotent charging confirmation and vignette purchase behavior.
- Route facts that expose pending, confirmed, and completed states separately.

**Must not edit:** Realtime prompt/tool definitions, shared contracts, frontend
components, Google provider adapters, or runtime configuration.

### Person C: contracts, Suzanne orchestration, and spoken formatting

**Owns only:**

- `backend/app/models/contracts.py`
- `backend/app/api/assistant.py`
- `backend/app/integrations/openai/realtime.py`
- `frontend/src/services/realtimeAssistantApi.ts`
- `frontend/src/types/contracts.ts`
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`
- `tests/backend/integration/test_realtime_api.py`
- `tests/backend/unit/test_openai_realtime.py`
- new `tests/backend/unit/test_day8_voice_contract.py`
- `docs/api/day8-voice-flows.md`

**Delivers:**

- Contracts for brand-wide partner enrichment, route opportunities, ordered
  charging plans, per-stop amenities, and route session memory facts.
- Tool responses that distinguish `suggested`, `confirmed`, and `completed`.
- Suzanne instructions to proactively mention the highest-value returned
  partner opportunity after route and amenity results.
- Suzanne instructions to say a benefit only from exact returned facts and to
  call a benefit simulated when the response marks it as a fixture benefit.
- Session-aware narration:
  - do not ask for charging again once the charging plan is confirmed;
  - do not ask for a vignette once the requirement is purchased or marked
    duplicate/completed;
  - do mention the next remaining requirement when a multi-stop plan is only
    partially completed.
- A single currency formatter for spoken amounts. EUR examples:
  - `16.50 euros`;
  - `16 euros and 50 cents`;
  - never `16 dollars and 50 cents euros`.
- No hard-coded spoken prices in the prompt. The tool result remains the source
  of truth.
- Multi-stop confirmation language that names the ordered plan and does not
  imply that only the first charger was added.

**Must not edit:** trip selection algorithms, partner fixtures, frontend visual
components, provider adapters, or wallet implementation.

### Person D: provider identity, places, runtime, and reliability

**Owns only:**

- `backend/app/integrations/google_maps/**`
- `backend/app/integrations/places/**`
- `backend/app/core/**`
- `backend/app/main.py`
- `.env.example`
- `docker-compose.yml`
- `docs/architecture/runtime.md`
- new `docs/configuration/day8-runtime.md`
- `tests/backend/unit/test_google_integrations.py`
- new `tests/backend/unit/test_day8_provider_identity.py`
- new `tests/backend/unit/test_day8_provider_reliability.py`

**Delivers:**

- Stable provider brand and place identity fields for charging and Places
  results.
- Normalized provider naming inputs without applying partner policy in the
  provider adapter.
- Bounded provider fan-out and useful diagnostics when partner enrichment
  inputs are unavailable.
- Verification that multi-stop provider geometry and waypoint ordering are
  preserved when the confirmed route is built.
- Clean local and Docker startup checks.

**Must not edit:** partner catalog, charging ranking, shared contracts,
Realtime prompts, frontend files, or wallet behavior.

### Integration lead

**Owns only:**

- `day8.md`
- `docs/README.md` when Day 8 is indexed
- integration branch merge commits and validation reports

The integration lead resolves ownership conflicts by returning them to the
owner of the conflicted file. Cross-owner decisions must be recorded in the
handoff note before merging.

## Required contract concepts

The exact field names are Person C's responsibility, but the shared contract
must represent these concepts:

```text
PartnerFact
  partnerId
  brand
  benefit
  benefitScope
  benefitSource
  verified

RouteOpportunity
  id
  type
  stopId or resultId
  partnerFact
  reason
  detourMinutes
  requiresRouteConfirmation
  status

ChargingPlan
  stops[] in route order
  complete
  totalChargingMinutes
  confirmed

RouteSessionFacts
  chargingPlanConfirmed
  confirmedChargingStopIds[]
  purchasedVignetteRequirementIds[]
  remainingRequirements[]
```

Raw provider payloads and route geometry must remain outside Realtime messages.
The frontend may receive full structured data for rendering; Suzanne receives
only compact verified facts.

## Acceptance scenarios

### Brand-wide partner matching

1. A Shell charging result with provider brand `Shell Recharge` is matched to
   the Shell brand record and Suzanne states the configured charging benefit.
2. Every matching MOL Plugee result receives the MOL Plugee brand benefit,
   regardless of location ID.
3. A McDonald's amenity result receives the configured restaurant benefit.
4. A nearby McDonald's without an explicit configured offer is described as
   nearby, not as discounted or free.
5. A hotel result matching a hotel brand receives the hotel benefit.
6. Ambiguous names and disabled brands produce no commercial claim.

### Route memory

1. Plan a route requiring charging and a vignette.
2. Confirm charging and purchase the vignette.
3. Ask for route status and start driving.
4. Suzanne does not repeat either completed requirement.
5. A duplicate purchase response is treated as completed, not as a new request.
6. A refresh or new route resets only the intended ephemeral session state.

### Currency wording

1. A vignette amount of `16.50` is spoken as `16.50 euros` or
   `16 euros and 50 cents`.
2. A charging cost and total route cost use the same EUR convention.
3. No response contains both `dollars` and `euros` for one amount.
4. Currency is not inferred from a free-text prompt; it comes from the typed
   tool response.

### Multiple charging stops

1. Use a route whose initial distance exceeds current safe range and whose
   destination remains beyond one maximum-charge range.
2. The service returns two or more ordered compatible stops.
3. Every stop is reachable from the preceding state with the safety buffer.
4. The initial voice response does not claim that the stops were added.
5. One charging confirmation applies the complete sequence.
6. The final route contains all charging stops in order, with correct duration,
   cost, partner facts, and nearby amenities.
7. A failed or incomplete sequence returns a stable actionable error and does
   not partially mutate the active route.

## Validation gate

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/backend -q
Set-Location frontend
npm run build
npm run lint
Set-Location ..
git diff --check
git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- .
```

Additional checks:

- all partner brand aliases normalize deterministically;
- all configured brand-wide benefits have eligible categories and a source;
- no partner benefit is narrated without a verified returned fact;
- no completed charging or vignette requirement is requested twice in one
  active route session;
- all multi-stop plans are ordered, reachable, and applied atomically;
- two-stop and three-stop fixtures are covered by backend tests;
- every successful tool call produces one spoken result and every failure has
  one actionable spoken error;
- no raw provider payload or geometry is sent to Realtime;
- browser acceptance passes for partner discovery, route memory, cost wording,
  and multi-stop charging;
- local and Docker startup remain stable.

## Branch protocol

Create the Day 8 branches from the validated Day 7 integration tip:

```text
integration/day8
|-- person-a/day8-partner-hmi
|-- person-b/day8-brand-catalog-trip-policy
|-- person-c/day8-contracts-voice-memory
`-- person-d/day8-provider-identity-runtime
```

Rules:

1. Person B publishes the brand-wide partner schema and fixture examples first.
2. Person C freezes shared contracts after reviewing the Person B schema.
3. Person D verifies provider identity fields before partner matching is merged.
4. Person B implements route policy and multi-stop behavior against the frozen
   contract.
5. Person A consumes structured facts and does not infer partner benefits in the
   UI.
6. Each branch includes focused tests and a handoff note.
7. No branch force-pushes or rebases another contributor's branch.
8. Conflicts return to the owner of the conflicted file.
9. The integration branch is not merged to `main` until manual acceptance of
   all scenarios and the complete validation gate.

## Definition of done

Day 8 is complete when brand-wide partner matching works for charging,
restaurants, amenities, and hotels; the catalog has broad corridor coverage;
Suzanne proactively narrates verified benefits; charging and vignette state is
remembered for the active route; EUR costs are spoken once and correctly;
multi-stop charging plans are selected and confirmed atomically; all focused
and full validation checks pass; and the golden demo can be completed without
repeated requirements, false partner claims, or manual recovery.