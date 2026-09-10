# Day 2 Deliverables: Route Planning and Voice Feedback

## Goal

By EOD Day 2, the driver can ask Suzanne for a route to a destination and
receive:

- a visually displayed route;
- the route distance in kilometres;
- the estimated travel time;
- a spoken route summary; and
- a spoken warning when the vehicle's current range is insufficient;
- immediate spoken feedback while the route is being calculated.

The target interaction is:

```text
Driver: Suzanne, take me to Budapest fast.

Suzanne: I've planned your route to Budapest. It's 243 km long and it will
         take approximately 2 hours 45 minutes.

Suzanne: Your car currently has an estimated range of 95 km, so it will not
         be able to cover this distance. Should I add a charging stop for you?
```

The wording may vary slightly, but the response must be based on returned
structured facts. Suzanne must not invent distance, duration, range, or
charging requirements.

## Voice feedback while processing

The frontend must not wait for the backend before giving the driver feedback.
After the request is locally accepted and processing starts, play a small
pre-recorded message queue, for example:

```text
Calculating your route, give me a few seconds.
I'm checking the distance and travel time now.
```

The messages must:

- be stored as local frontend audio assets;
- play in order while the backend request is running;
- start independently of backend TTS latency;
- stop immediately when the request finishes or errors;
- never play after a known error; and
- never claim route facts that the backend has not returned.

The final backend response replaces the filler queue with one natural,
conversational route summary. The frontend must not wait for the filler audio
to finish before showing the route.

## Explicitly out of scope

Do not implement any of the following on Day 2:

- POI search or recommendations;
- partner offers or commerce;
- restaurant, toll, or payment flows;
- editing or rerouting an existing route;
- adding the charging stop after the driver answers;
- weather or traffic alerts;
- conversational follow-ups beyond the charging question;
- route alternatives or route comparison;
- route confirmation buttons.

Day 2 ends when the route is displayed and Suzanne asks whether a charging
stop should be added. A later milestone can implement the driver's answer.

## Shared Day 2 contract

The existing `AssistantResponse` remains the response envelope. For route
requests, `route` must be populated instead of `null`.

`RouteResponse` must contain, at minimum:

- `origin`;
- `destination`;
- `stats.totalDistanceKm`;
- `stats.totalDurationMinutes`;
- `geometry` for visual rendering;
- `stops`, initially empty unless the route provider returns a required route
  stop; and
- `alerts`, including a vehicle-range warning when applicable.

The backend and frontend may add a small explicit range result to the shared
contract if the existing `RouteAlert` shape is not sufficient. That result
must describe the requirement to consider charging without representing a
charging stop that has not been selected.

The frontend must consume structured route fields. It must not parse
`spokenResponse` to calculate distance, duration, or charging requirements.

## Person A: Frontend and route HMI

- Add a route view to the existing assistant screen.
- Render `route.geometry` visually as a route line on a map or route canvas.
- Display the route origin and destination.
- Display total distance in kilometres.
- Display estimated duration in hours and minutes.
- Display the selected route priority.
- Display a clear vehicle-range warning when the backend returns one.
- Display route loading, empty, error, and unavailable-route states.
- Keep the route display read-only.
- Do not add POI cards, partner cards, route-editing controls, or charging-stop
  selection controls.
- Keep the existing microphone, transcript, intent, and audio playback flow.
- Play the backend's spoken route summary and charging question.
- Add focused frontend verification for a populated route response and a route
  response with a range warning.

## Person B: Backend and deterministic route service

- Add a minimal route service behind a provider-neutral routing interface.
- Accept the destination and priority from `AssistantIntent`.
- Resolve the current origin from the configured demo vehicle position or the
  agreed local origin fixture.
- Geocode the Day 2 demo destination and at least one second destination.
- Request a route for the selected priority and normalize the provider result
  into `RouteResponse`.
- Return route geometry, distance, and duration as typed values.
- Keep distance in kilometres and duration in minutes.
- Load `data/vehicles/telemetry.json` through the existing repository boundary.
- Compare route distance with the vehicle's `estimatedRangeKm`.
- Return a deterministic vehicle-range warning when the route cannot be
  covered with the current estimated range.
- Make the warning ask whether a charging stop should be added; do not add or
  select a charging stop yet.
- Ensure route facts are calculated by deterministic code, not invented by the
  language model.
- Add tests for:
  - an arbitrary destination returning a populated route;
  - distance and duration unit conversion;
  - a route within estimated range;
  - a route exceeding estimated range;
  - provider failure and invalid destination handling.

## Person C: AI and voice orchestration

- Preserve the existing Whisper transcription and structured destination and
  priority extraction.
- Pass the extracted intent to the deterministic route service through the
  backend orchestration boundary.
- Generate a concise, human, conversational spoken route summary from the
  returned route facts.
- Include destination, distance, and estimated duration in the spoken summary.
- When the vehicle-range result requires it, ask exactly one concise question
  about adding a charging stop.
- Use only structured backend facts for spoken distance, duration, range, and
  charging wording.
- Keep the spoken response in English for the Day 2 demo and configure
  transcription language consistently with the supported driver language.
- Keep TTS output concise and natural enough for repeated route narration.
- Do not generate filler messages through the backend on every request; the
  frontend owns the pre-recorded processing messages so they start immediately.
- Add tests with fake route data and fake OpenAI clients so route narration is
  deterministic and does not require live provider calls.

## Person D: Platform and integration

- Integrate the agreed routing provider, such as OpenRouteService, behind the
  provider-neutral boundary used by Person B.
- Add routing-provider configuration through `.env` and keep all provider keys
  backend-only.
- Implement provider timeouts, bounded retries, and clear error handling for
  geocoding and route requests.
- Add a deterministic local fixture or mock-routing mode for development and
  tests when the provider key is missing or the provider is unavailable.
- Ensure provider responses are normalized into the internal route shape and
  do not leak provider-specific formats into the frontend.
- Verify routing is not hard-coded only for Budapest.
- Ensure the frontend and backend run together on their documented local
  ports: `5173` and `8000`.
- Keep CORS configured for the local frontend origin.
- Ensure `.env` loading works for routing and OpenAI provider keys without
  committing secrets.
- Add or update health and startup checks for the route provider configuration.
- Document the required routing provider key and the local fallback or fixture
  behavior used by tests.
- Add useful diagnostics for route requests, including:
  - total request duration;
  - geocoding duration;
  - routing duration;
  - provider failures; and
  - whether the real provider or local fallback was used.
- Add an end-to-end smoke test covering:
  - destination request;
  - geocoding;
  - route-provider call or local fallback;
  - normalized route response;
  - vehicle telemetry range check; and
  - frontend-compatible `AssistantResponse` output.
- Verify the end-to-end route flow from a clean local setup.

Person D's main Day 2 outcome is a clean local runtime that can return a route
from the real provider or deterministic fallback, with clear errors and no
secret leakage.

## Day 2 collaboration workflow

Each person may give their assigned task directly to Copilot in VS Code. The
team must provide Copilot with the relevant section of this document, the
current contracts, and the files that person owns before asking it to change
code.

### File ownership

Each file has one owner. Copilot must receive an explicit file allowlist and
must not edit files outside that list.

#### Person A owns

May edit:

- `frontend/**`
- frontend-focused tests

Must not edit:

- `backend/app/**`
- `backend` tests
- `DAY2.md`
- shared backend contracts without agreement from Person B

#### Person B owns

May edit:

- `backend/app/api/**`
- `backend/app/services/**`
- `backend/app/models/**`
- `backend/app/core/**`
- backend integration and deterministic-service tests

Must not edit:

- `backend/app/integrations/openai/**`
- Person C's AI adapter tests
- `frontend/**`
- `DAY2.md`

#### Person C owns

May edit:

- `backend/app/integrations/openai/**`
- AI adapter and narration tests

Must not edit:

- `backend/app/api/assistant.py`
- `backend/app/services/**`
- `backend/app/models/**`
- `frontend/**`
- `DAY2.md`

#### Person D owns

May edit:

- routing-provider adapter files agreed with Person B;
- runtime configuration and environment-loading files;
- Docker and startup files;
- health checks and end-to-end smoke-test wiring.

Must not edit:

- Person C's OpenAI implementation;
- Person A's frontend files;
- Person B's route business rules;
- `DAY2.md` unless the team lead asks for a documentation change.

Shared-file rule:

- `backend/app/api/assistant.py` has one owner: Person B.
- `backend/app/services/assistant/**` has one owner: Person B.
- `backend/app/models/contracts.py` has one owner: Person B.
- `DAY2.md` has one owner: the team lead.
- If a person needs a change outside their ownership, they must request it
  from the owner instead of editing it in their own branch.

Copilot prompt rule:

```text
You may edit only the files in my ownership list. Do not edit, rename, or
create files outside that list. Use existing interfaces. If an interface is
insufficient, stop and report the required change instead of modifying the
other person's files.
```

- Person A, B, C, and D work on separate feature branches.
- Before implementation, agree on shared contract changes and record them in
  the branch that owns the contract.
- Avoid having multiple agents create or substantially rewrite the same file.
- Person B owns route orchestration and deterministic range rules.
- Person C owns the AI provider adapter and route narration behavior.
- Person D owns routing-provider integration, fallback mode, configuration,
  resilience, diagnostics, and smoke-test wiring.
- Use fake route data and fake AI clients so each person can test without
  waiting for another person or a live external provider.
- Keep commits small and scoped to one person's task.
- Open a PR for each feature branch and merge contract or interface changes
  before dependent implementation changes.
- After a PR is merged, each person updates local `main` before continuing:

  ```powershell
  git switch main
  git pull --ff-only origin main
  ```

- If work continues on an existing feature branch, rebase it on the updated
  `main` before the next PR:

  ```powershell
  git fetch origin
  git rebase origin/main
  ```

- Resolve conflicts deliberately and run the focused tests before pushing the
  rebased branch.

### Fake AI provider rule

Person B must build against the existing `AssistantAIModule` interface, not
against the OpenAI SDK. Person B can use a fake implementation in tests:

```text
API route -> AssistantService -> AssistantAIModule

tests:       FakeAIModule
production:  OpenAIAssistantModule
```

Both implementations must return the same `AIResult` shape. Person B's route
and orchestration code must not change when Person C's real OpenAI adapter is
merged. Person C implements the real adapter behind the same interface and
tests it with a fake OpenAI client.

If the interface must change, update it first, agree on the change, and merge
that contract change before dependent implementation work continues.

The EOD integration owner should merge the completed branches in dependency
order, run the full acceptance test below, and confirm that the final result
still excludes POIs, partner commerce, route editing, and charging-stop
selection.

## End-of-day acceptance test

1. Start the backend and frontend.
2. Say or submit a request for a destination that is not hard-coded, for
   example: `Suzanne, take me to Budapest fast`.
3. Verify the backend returns a populated `AssistantResponse.route`.
4. Verify the route contains non-empty geometry.
5. Verify the frontend displays the route visually.
6. Verify the displayed distance is in kilometres.
7. Verify the displayed duration is in hours and minutes.
8. Verify Suzanne speaks a summary containing the destination, distance, and
   duration.
9. Verify the backend reads the vehicle telemetry fixture.
10. For a route longer than the vehicle's estimated range, verify Suzanne says
    that the car cannot cover the distance and asks whether to add a charging
    stop.
11. Verify no POIs, partner recommendations, route-editing controls, or
    charging-stop selection are shown.

Day 2 is complete when the route can be requested for an arbitrary destination,
seen visually, and described accurately by voice, with the telemetry-based
charging question as the final interaction.
