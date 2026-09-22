# Day 9: Finishing Reliability, Route Intelligence, and Driving HMI

## Purpose

Day 9 is the final finishing pass for the Suzanne prototype. It closes the
remaining voice, route-planning, provider, country-rule, driving-mode, and
presentation gaps while preserving the local modular-monolith architecture.

The priority order is:

1. Safety and deterministic route correctness.
2. Realtime session reliability and concise voice behavior.
3. Driving-mode clarity and telemetry truth.
4. Route weather, place enrichment, and European vignette coverage.
5. UI polish and regression coverage.

No implementation should invent route, range, weather, charging, review,
partner, price, or payment facts. All such facts must come from deterministic
services or explicitly marked demo fixtures.

## Scope

Day 9 delivers:

- A swipeable battery card with telemetry and structured Google place
  suggestions, including optional photos, summaries, ratings, review counts,
  and top keywords.
- A driving-mode map with buildings hidden and a heading-aware driver arrow
  instead of the normal blue vehicle dot.
- Weather conditions and alerts integrated into the planned route.
- Reliable Stop-before-handshake and Start-again behavior for Suzanne.
- Listening-jingle playback only after the Realtime connection is confirmed.
- Concise route acknowledgements with no immediate "route is still processing"
  narration.
- Strict telemetry-backed range and battery narration.
- Reliable Riga route handling with precise errors when a safe route truly
  cannot be formed.
- Two or more charging stops selected and confirmed in one spoken request,
  spaced according to vehicle range and safety buffer.
- Czechia, Slovakia, Slovenia, and other required European vignette rules.
- Final frontend, backend, browser, runtime, and documentation validation.

## Ownership Rules

Each implementation file has one owner. Reviews are encouraged, but edits go
to the owner listed here.

### Shared contract owner: Person C

- `backend/app/models/contracts.py`
- `frontend/src/types/contracts.ts`
- `backend/app/api/assistant.py`
- `backend/app/integrations/openai/realtime.py`
- `frontend/src/services/realtimeAssistantApi.ts`
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`

### Person A: frontend and driving HMI file ownership

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/features/map/**`
- `frontend/src/features/trip/**`
- `frontend/src/features/assistant/components/**`
- `tests/frontend/**`
- `tests/e2e/**`

### Person B: deterministic trip and telemetry policy file ownership

- `backend/app/services/trip/**`
- `backend/app/services/recommendation/**`
- `backend/app/services/vehicle/**`
- `data/vehicles/**`
- `tests/backend/unit/test_route_service.py`
- `tests/backend/unit/test_day8_multi_stop_charging.py`
- new `tests/backend/unit/test_day9_route_reliability.py`
- new `tests/backend/unit/test_day9_telemetry_policy.py`

### Person C: AI, voice, and Realtime lifecycle file ownership

- `backend/app/models/contracts.py`
- `backend/app/api/assistant.py`
- `backend/app/integrations/openai/realtime.py`
- `frontend/src/services/realtimeAssistantApi.ts`
- `frontend/src/types/contracts.ts`
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`
- `tests/backend/integration/test_realtime_api.py`
- `tests/backend/unit/test_openai_realtime.py`
- new `tests/backend/unit/test_day9_voice_contract.py`
- `docs/api/day9-voice-flows.md`

### Person D: providers, weather, country rules, and runtime file ownership

- `backend/app/integrations/google_maps/**`
- `backend/app/integrations/places/**`
- new `backend/app/integrations/weather/**`
- `backend/app/core/**`
- `backend/app/main.py`
- `data/routes/**`
- `.env.example`
- `docker-compose.yml`
- `docs/architecture/runtime.md`
- new `docs/configuration/day9-runtime.md`
- `tests/backend/unit/test_google_integrations.py`
- new `tests/backend/unit/test_day9_weather.py`
- new `tests/backend/unit/test_day9_country_rules.py`
- new `tests/backend/unit/test_day9_provider_resilience.py`

### Integration lead

- `day9.md`
- `docs/README.md`
- final handoff and validation report

The integration lead does not resolve conflicts by editing another person's
owned implementation file. Conflicts return to that file's owner.

| Role | Primary file ownership |
|---|---|
| Person A | Frontend HMI, map, trip presentation, and browser tests |
| Person B | Deterministic trip services, charging, telemetry, and route tests |
| Person C | Shared contracts, Realtime lifecycle, voice behavior, and API tests |
| Person D | Google integrations, weather, country rules, runtime, and provider tests |

The four person roles have explicit file ownership: Person A owns the frontend,
Person B owns deterministic trip intelligence, Person C owns contracts and
Realtime voice, and Person D owns providers, weather, country rules, and
runtime integration.

## Shared Contract Freeze

Person C publishes the contract changes before dependent implementation begins.
The contract must represent:

- Realtime connection readiness and session generation.
- Structured place summary, photo reference, rating, review count, keywords,
  and provider/source metadata.
- Route-segment weather facts and weather alerts.
- Ordered multi-stop charging plans and per-stop state.
- Remaining and completed route requirements.
- Telemetry-backed range facts used for narration.
- Stable error codes distinguishing invalid destinations, provider failures,
  missing charging candidates, and unsafe charging sequences.

Raw Google payloads, route geometry, and map-only presentation data must not be
sent to Realtime.

## Person A Deliverables: Frontend and Driving HMI

### Battery card sliding window

- Keep battery percentage, estimated range, consumption, and telemetry status
  visible as the primary card state.
- Add swipe, keyboard, and accessible previous/next controls.
- Show structured suggested locations without inferring facts:
  - place name and category;
  - rating and review count;
  - short provider summary;
  - top three returned keywords;
  - optional photo;
  - provider/source state.
- Handle missing photos, summaries, reviews, and keywords gracefully.
- Keep the card stable on desktop and mobile widths.

### Driving mode

- Hide 3D buildings when `drivingActive` becomes true.
- Restore the overview map style when returning to the main route.
- Replace the blue origin/current-position dot with a driver arrow.
- Rotate the arrow using route or vehicle heading.
- Preserve readable roads, route geometry, destination, and mandatory stops.
- Verify behavior with and without a Google map ID, since cloud map styling
  may override local styling.

### Weather UI

- Remove the hardcoded weather text from `App.tsx`.
- Render structured route weather and severity alerts.
- Show a clear unavailable state without blocking route presentation.

### Browser acceptance

Cover:

- Battery-card navigation and fallback content.
- Google place details with and without optional fields.
- Driving-mode building visibility and driver-arrow orientation.
- Route weather success and unavailable states.
- Two-stop route rendering and completion state.
- Start, stop, and immediate restart of Suzanne.

Person A must not edit backend services, provider adapters, route rules,
shared contracts, or Realtime instructions.

## Person B Deliverables: Trip Intelligence and Telemetry

### Riga route failure

- Reproduce the current `NO_SAFE_CHARGING_PLAN` response for Riga.
- Determine whether the cause is geocoding, route geometry, charging-candidate
  coverage, route-progress calculation, or the range policy.
- Improve candidate discovery or deterministic fallback behavior where safe.
- Never silently produce an unsafe route.
- Return a stable, actionable error when no safe plan exists.
- Add a regression test for the Riga request and its expected successful or
  explicitly unavailable outcome.

### Multi-stop charging

- Accept one spoken request for two or more chargers, such as Vienna to Berlin.
- Select chargers in route order.
- Use current telemetry range for the first leg.
- Use `max_charged_range_km` for later legs.
- Respect the configured safety buffer.
- Reject duplicate stops, loops, unreachable transitions, and incomplete plans.
- Confirm the complete ordered plan atomically.
- Preserve every stop's duration, cost, partner facts, and nearby amenities.

### Telemetry truth

- Make range, battery, consumption, and charging-feasibility facts originate
  from the active telemetry service or fixture.
- Ensure route, driving, charging, and warning responses use the same source.
- Add tests for changed battery percentage, changed estimated range, and
  maximum charged range.

### Route-session state

- Preserve completed charging and vignette requirements.
- Expose pending, confirmed, completed, and remaining states consistently.
- Prevent completed requirements from being requested again.

Person B must not edit Realtime prompts, shared contracts, Google adapters,
frontend components, or country-rule fixtures.

## Person C Deliverables: Suzanne and Realtime Reliability

### Handshake cancellation and restart

- Add a session generation or connection token.
- Invalidate an in-progress connection when Stop is pressed.
- Ensure stale handshake promises cannot publish a channel, stream, audio,
  state, or event into a newer session.
- Close the peer connection, data channel, microphone tracks, and audio for
  every cancelled attempt.
- Ensure Start after an interrupted handshake creates exactly one usable
  session.
- Define and test the authoritative connection-confirmed event.

### Listening jingle

- Do not play the jingle when Start is merely pressed.
- Play it exactly once after the Realtime session, remote description, and data
  channel establish a confirmed connection.
- Do not play it after a failed, cancelled, or timed-out handshake.

### Concise route narration

- Give one short acknowledgement while route planning starts.
- Do not say "route is still processing" immediately after the request.
- Do not repeat the acknowledgement after the tool returns.
- Speak once when the deterministic route result arrives.
- Keep the result concise and based only on returned facts.

### Telemetry-first voice policy

Suzanne must always use returned telemetry-backed facts for:

- current battery;
- estimated range;
- consumption;
- charging feasibility;
- remaining range-related warnings;
- charging-stop justification.

Suzanne must not estimate range from route distance or conversational context.

### Multi-stop voice flow

- Extend tool schemas and compact narration facts for a complete charging plan.
- Handle prompts requesting multiple chargers in one turn.
- Confirm the returned ordered plan rather than claiming only the first charger
  was added.
- Report all required stops once, without repetition.

Person C must not edit trip algorithms, provider implementations, frontend
visual components, country fixtures, or wallet logic.

## Person D Deliverables: Providers, Weather, and Country Rules

### Google place enrichment

- Normalize place summaries, photos, ratings, review counts, and stable
  keyword/category facts.
- Preserve stable place IDs for frontend navigation.
- Keep optional fields optional.
- Treat partial provider failures separately from complete route failures.
- Keep provider identity separate from partner-benefit policy.

### Route weather

- Add a provider interface and deterministic offline fixture implementation.
- Support weather at route segments or sampled route locations.
- Normalize temperature, condition, location, severity, and timestamps where
  available.
- Convert severe conditions into route alerts.
- Keep route planning usable when the provider is unavailable.

### European vignette rules

Add deterministic rules and tests for at least:

- Czechia;
- Slovakia;
- Slovenia;
- existing Austria-Hungary behavior;
- country aliases and code forms used by providers.

Avoid broad substring matching that produces false positives. Add corridor
fixtures covering multiple borders and requirements.

### Riga and provider diagnostics

Add diagnostics that distinguish:

- invalid destination;
- routing failure;
- Google Places failure;
- no charging candidates;
- no safe charging sequence;
- provider timeout or partial response.

### Runtime

- Add weather configuration without exposing secrets.
- Update health/config diagnostics.
- Keep health usable when OpenAI, Google, or weather providers are disabled.
- Document local and Docker startup behavior.

Person D must not edit partner catalogs, charging ranking, shared contracts,
Realtime prompts, frontend files, or wallet behavior.

## Additional Improvements Found During Repository Review

These are included because they affect the finished-demo quality:

- `backend/app/api/assistant.py` currently returns an empty opportunities list
  for route POI searches even though recommendation logic exists.
- Frontend component and browser coverage is substantially thinner than the
  backend coverage and needs a final regression layer.
- The weather label in `frontend/src/App.tsx` is hardcoded.
- Google Places lacks a first-class photo, summary, and keyword contract.
- Map styling hides buildings statically, but driving-mode runtime changes need
  explicit verification with tilt and map IDs.
- Route errors need precise classifications for both debugging and voice
  recovery.
- Documentation still describes some implemented areas as bootstrap or future
  work and should be reconciled with the final implementation.
- Currency formatting and route-price facts should receive a final regression
  pass in both UI and voice.
- Every successful tool call should produce one spoken result, and every
  failure should produce one actionable spoken error.

## Integration Sequence

1. C freezes contracts and error codes.
2. D publishes provider fakes, weather normalization, and country-rule tests.
3. B fixes route reliability, charging sequencing, telemetry policy, and route
   session state.
4. C completes Realtime cancellation, readiness, jingle, and narration logic.
5. A consumes structured results and completes the driving HMI.
6. The integration lead runs the full validation gate and updates documentation.

No implementation branch should wait for a live provider. Fake providers and
fixtures must support all focused tests.

## Acceptance Scenarios

### Realtime lifecycle

1. Start Suzanne.
2. Stop before the handshake completes.
3. Start Suzanne again.
4. Exactly one session becomes active.
5. The jingle plays only for the confirmed session.
6. No stale audio, microphone track, channel, or state update survives.

### Concise route conversation

1. Ask for a route.
2. Suzanne acknowledges once.
3. Suzanne remains quiet while planning runs.
4. Suzanne gives one returned route summary.
5. Suzanne does not repeat processing language or unsupported range claims.

### Riga

1. Ask for Riga.
2. Receive a safe route with suitable charging, or a precise actionable
   unavailable result.
3. Do not expose an unexplained `422 Unprocessable Content` response.

### Multi-stop charging

1. Request Vienna to Berlin with two chargers.
2. Return an ordered, reachable plan.
3. Confirm the plan once.
4. Apply every stop atomically.
5. Preserve correct route order, duration, cost, and partner facts.

### Driving mode

1. Plan a route.
2. Start driving by voice.
3. Hide 3D buildings.
4. Show the heading-aware driver arrow.
5. Keep roads and mandatory stops readable.

### Weather and vignettes

1. Plan routes crossing supported European countries.
2. Show route weather or a provider-unavailable fallback.
3. Return the correct vignette requirements for Czechia, Slovakia, Slovenia,
   Austria, and Hungary.
4. Do not repeat purchased requirements.

### Suggested places

1. Open the battery-card window.
2. Cycle through returned place suggestions.
3. Show available ratings, review counts, summaries, keywords, and photos.
4. Never fabricate missing data.

## Final Validation Gate

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

Also verify:

- frontend component tests;
- browser acceptance tests;
- Riga route regression;
- handshake cancellation and restart;
- jingle timing;
- weather provider fallback;
- multi-stop charging;
- European vignette matrix;
- telemetry-backed narration;
- Docker startup and health checks;
- manual golden demo from route request through driving mode.

## Definition of Done

Day 9 is complete when the golden demo can be run from a clean local start:
Suzanne connects reliably, speaks briefly and truthfully, plans Riga and
multi-stop routes safely, uses telemetry for range facts, presents weather and
place suggestions, supports European vignette requirements, switches cleanly
to a readable driving map, and passes the complete automated validation gate.
