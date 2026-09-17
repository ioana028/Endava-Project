# Day 7: Partner Intelligence, Scenic Routing, Voice Naturalness, and Release Hardening

## Purpose

Day 7 is the final feature and hardening pass before the PR. The goal is to
make Suzanne feel informed and natural while keeping every route, charger,
partner, and commerce fact deterministic and testable.

Day 7 does not add real payments, real bookings, a database, session storage,
a wake word, or new microservices. Partner recommendations remain advisory:
Suzanne may surface a returned benefit, but never forces a partner or invents a
commercial claim.

## Product outcomes

By the end of Day 7:

- `start_driving` returns HTTP 200 and activates the existing presentation-only
driving state without replanning.
- Vienna-Budapest and Vienna-Berlin expose the real Google charging plan,
including every mandatory stop required by initial and post-charge range.
- Partner enrichment is visible when a returned Google or fixture result matches
a partner record by stable ID, provider brand, or normalized location name.
- Budapest route results can surface relevant partner charging, hotel, and
restaurant options with concrete benefits.
- Partner benefits are never narrated for a non-partner result, a vignette
requirement without an explicit benefit, or an unverified provider result.
- `SCENIC` produces a distinct route preference using provider-supported scenic
routing where available and deterministic scenic ranking where it is not.
- Suzanne speaks in a natural, low-repetition style. She does not prepend
"Got it", "Alright", or "Absolutely" to every response and does not repeat
acknowledgements after a tool has already acknowledged the request.
- Every successful tool call produces a short spoken result; failures produce a
clear actionable explanation instead of silence.
- The final browser flow is demoable from route planning through partner
discovery, scenic routing, driving mode, commerce, and refresh behavior.

## Known Day 7 defects to fix first

### Start driving 503

The API already delegates `start_driving` to `route_service`, but the current
RouteService must expose the implementation. It must:

- require the current `routeId`;
- reject stale route context with the stable error envelope;
- return `route_state_facts()` as the compact driving response;
- preserve route geometry, route ID, destination, stops, and charging facts;
- never call route planning or the route provider again.

### Partner silence

The current partner data is too small and partner enrichment is not consistently
visible in route-aware hotel and restaurant results. Day 7 must add useful
partner fixtures and make enrichment observable in the returned typed facts.
Suzanne must mention a partner only when the response contains a concrete
benefit, for example:

```text
There is a ChargePoint location on your route with 10% off charging sessions.
```

No benefit means no commercial claim.

### Scenic routing

`SCENIC` exists in the priority vocabulary but needs an end-to-end product
meaning. It must not silently behave like `FASTEST`. The provider adapter may
use a supported scenic preference; offline mode must use deterministic scenic
fixtures or ranking metadata and clearly label the result as an estimate when
provider scenic data is unavailable.

## Role split and ownership

No implementation file may have two owners. Review is encouraged, but edits go
to the owner listed below.

### Person A: final HMI, partner presentation, and browser acceptance

**Owns only:**

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/features/map/**`
- `frontend/src/features/navigation/**`
- `frontend/src/features/commerce/components/**`
- `frontend/src/features/assistant/components/AssistantStatus.tsx`
- `frontend/src/features/trip/components/RouteSummary.tsx`
- `frontend/src/assets/**`
- `tests/frontend/**`
- `tests/e2e/frontend/**`

**Delivers:**

- Partner badge/benefit presentation only when structured partner data exists.
- Clear distinction between ordinary results and partner results.
- Scenic route visual treatment without inventing scenic facts.
- Driving-mode presentation and final map camera polish.
- Booking and vignette confirmation panel behavior stays temporary and
accessible.
- Browser acceptance tests for start driving, partner visibility, scenic mode,
commerce confirmation, refresh reset, and no silent successful action.

**Must not edit:** backend services, provider adapters, shared contracts,
Realtime instructions, or `data/partners/partners.json`.

### Person B: deterministic trip, partner, and route policy

**Owns only:**

- `backend/app/services/trip/**`
- `backend/app/services/recommendation/**`
- `backend/app/services/commerce/**`
- `backend/app/services/wallet/**`
- `data/partners/partners.json`
- `data/commerce/**`
- `tests/backend/unit/test_route_service.py`
- `tests/backend/unit/test_day5_trip_policy.py`
- `tests/backend/unit/test_day6_commerce.py`
- `tests/backend/unit/test_day6_wallet.py`
- new `tests/backend/unit/test_day7_partner_policy.py`
- new `tests/backend/unit/test_day7_scenic_policy.py`

**Delivers:**

- Implement `RouteService.start_driving(route_id)` using current route facts.
- Add tests for HTTP/service success, stale route rejection, and no provider call.
- Expand `partners.json` with concrete charging, hotel, and restaurant
locations across Vienna-Budapest and Vienna-Berlin.
- Give every location a stable ID, category, coordinates, provider brands,
benefit, rating, detour, and relevant amenities.
- Add partner matching by stable ID first, provider brand/location name second,
with no fuzzy match that can create a false commercial claim.
- Ensure partner ranking is secondary to route relevance, safety, explicit
priority, rating, and detour.
- Add scenic ranking metadata and deterministic offline scenic behavior.
- Ensure post-charge range and multi-stop selection remain correct for long
routes.

**Must not edit:** frontend files, `backend/app/models/contracts.py`, API
wiring, Realtime instructions, Google adapters, or `.env` configuration.

### Person C: contracts, Suzanne voice, and orchestration

**Owns only:**

- `backend/app/integrations/openai/realtime.py`
- `backend/app/api/assistant.py`
- `backend/app/models/contracts.py`
- `frontend/src/services/realtimeAssistantApi.ts`
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`
- `frontend/src/types/contracts.ts`
- `tests/backend/integration/test_realtime_api.py`
- `tests/backend/unit/test_openai_realtime.py`
- new `tests/backend/unit/test_day7_voice_contract.py`
- `docs/api/day6-voice-flows.md`
- new `docs/api/day7-voice-flows.md`

**Delivers:**

- Freeze the Day 7 contract for `start_driving`, partner enrichment, scenic
priority, and compact partner facts before branch implementation.
- Wire the `start_driving` tool to the route service result and preserve the
current route ID.
- Rewrite Suzanne instructions to use varied, concise acknowledgements only
when useful. Avoid habitual filler and repeated confirmations.
- Require a spoken acknowledgement for every successful tool result and a
clear spoken error for every failed tool result.
- Narrate concrete partner benefits only from returned facts.
- Narrate scenic mode as a preference, never as a guaranteed view or road
quality claim unless the provider returned that fact.
- Keep route geometry and raw provider payloads out of Realtime messages.

**Must not edit:** Person A visual components, Person B trip/partner services,
Person D provider/runtime files, or `data/partners/partners.json`.

### Person D: provider, runtime, and release reliability

**Owns only:**

- `backend/app/integrations/google_maps/**`
- `backend/app/integrations/places/**`
- `backend/app/main.py`
- `backend/app/core/settings.py`
- `backend/app/core/errors.py`
- `.env.example`
- `docker-compose.yml`
- `docs/architecture/runtime.md`
- `docs/configuration/day6-runtime.md`
- new `docs/configuration/day7-runtime.md`
- `tests/backend/unit/test_google_integrations.py`
- `tests/backend/unit/test_day6_performance.py`
- new `tests/backend/unit/test_day7_provider_reliability.py`

**Delivers:**

- Verify Google Routes scenic preference behavior and define the offline
fallback without hiding provider failures.
- Preserve Google place review counts, types, provider brands, and stable IDs
needed for partner matching.
- Ensure bounded route/Places fan-out and useful timeout/quota diagnostics.
- Add provider health diagnostics for scenic capability and partner enrichment
inputs without exposing secrets or raw payloads.
- Verify a clean Docker/local startup and stable error envelopes.

**Must not edit:** trip ranking, partner fixtures, Realtime tools/prompts,
shared contracts, frontend files, commerce/wallet services, or route policy.

### Integration lead

**Owns only:**

- `day7.md`
- `docs/README.md` when the new day is indexed
- integration branch merge commits and validation reports

The integration lead does not repair another owner’s implementation conflict
silently. Conflicts return to the owning person unless the owner explicitly
agrees to a documented resolution.

## Partner data contract

Every location partner must contain:

```json
{
  "id": "partner-hotel-budapest-001",
  "kind": "location",
  "name": "Riverside Hotel Budapest",
  "brand": "Riverside Hotels",
  "category": "hotel",
  "categories": ["hotel"],
  "providerBrands": ["Riverside Hotels"],
  "coords": [19.04, 47.50],
  "rating": 4.6,
  "tag": "Partner hotel near the destination",
  "benefit": "10% off partner room rates",
  "amenities": ["wifi", "parking"],
  "enabled": true,
  "detourMinutes": 4
}
```

A partner record without a concrete benefit may enrich identity but must not be
narrated as a promotion. Network records without coordinates are not direct
stop recommendations.

## Voice direction

Suzanne should sound like a composed executive assistant, not a scripted
call-center agent.

Avoid habitual openers:

- "Got it."
- "Alright."
- "Absolutely."
- "Sure thing."
- "I can help with that."

Preferred behavior:

- answer directly when the request is clear;
- acknowledge only when a provider call takes noticeable time;
- vary sentence openings naturally;
- never repeat the same acknowledgement and result;
- keep routine confirmations under two short sentences;
- state uncertainty or provider limitations plainly.

Examples:

```text
Driver: Take me to Budapest.
Suzanne: Budapest is 250 kilometres away. I found one charging stop and a
partner location with a returned benefit.

Driver: What's scenic?
Suzanne: I found a scenic alternative. It is longer than the fastest route by
18 minutes.
```

## Day 7 acceptance scenarios

1. **Start driving:** plan a route, say `Let's get going`, receive HTTP 200,
see driving mode, and verify no second route-provider call.
2. **Partner charging:** on Vienna-Budapest, Suzanne names a returned charging
partner and its exact benefit, if one exists.
3. **Partner hotel:** search hotels near Budapest and see at least one partner
hotel only when its provider result matches a partner record.
4. **Partner restaurant:** search restaurants near Budapest and see a concrete
restaurant benefit without suppressing generic restaurants.
5. **Scenic route:** say `Take the scenic route to Budapest`; verify priority
`SCENIC`, distinct route facts or an explicit unavailable fallback.
6. **No filler:** repeat route, POI, and commerce requests; Suzanne does not
use the same acknowledgement every time.
7. **Long route:** Vienna-Berlin returns all mandatory Google chargers required
by initial and post-charge range.
8. **Provider failure:** disable or invalidate a provider and receive a stable,
spoken error rather than silence or a stack trace.
9. **Refresh:** refresh resets ephemeral route, commerce, partner, and driving
state as documented.

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

- `start_driving` returns 200 with current route context and 409 for stale
context;
- no `start_driving` request calls route planning or a provider;
- partner result identity and benefit are present in compact facts;
- no partner benefit is narrated without an exact returned benefit;
- scenic priority is preserved from voice tool through route provider;
- all route and POI provider requests remain bounded;
- Suzanne produces a spoken success or error for every tool call;
- no habitual acknowledgement appears in every scripted response;
- all partners have stable IDs and valid coordinates where location records
claim to be direct stops;
- all tests and handoff notes identify one owner per implementation file.

## Definition of done

Day 7 is complete when the start-driving 503 is fixed and tested, the partner
catalog is meaningfully expanded, partner identity and benefits are surfaced
without false claims, scenic routing has a real deterministic/provider-backed
meaning, Suzanne speaks naturally without filler repetition, successful and
failed tools are never silent, long-route charging remains safe, local startup
and provider failures are stable, the complete validation gate passes, and the
final golden scenarios are accepted on `integration/day7`.

## Branch protocol

Create the branch from the validated Day 6 tip:

```text
integration/day7
|-- person-a/day7-final-hmi
|-- person-b/day7-partners-trip-policy
|-- person-c/day7-voice-naturalness
`-- person-d/day7-provider-scenic-runtime
```

Rules:

1. Person C freezes shared contracts before implementation branches merge.
2. Person B publishes the partner schema and fixture examples before Person C
writes partner narration.
3. Person D confirms provider scenic capabilities before Person B finalizes the
offline scenic policy.
4. Each branch edits only its owned files.
5. Every branch includes focused tests and a handoff note.
6. No branch force-pushes or rebases another contributor's work.
7. Merge conflicts return to the owner of the conflicted file.
8. The integration branch is not merged to `main` until the complete gate and
manual acceptance scenarios pass.
