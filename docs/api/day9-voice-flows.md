# Day 9 Voice Flows

This document defines the Person C Realtime contract for the final Suzanne
prototype pass.

## Connection lifecycle

The browser creates a new session generation for every Start attempt. Stop
invalidates the generation, aborts the session and tool requests, closes the
peer connection and data channel, stops microphone tracks, and releases audio.
Async work from an invalid generation must not publish state, audio, events, or
connection references into a later session.

The authoritative browser readiness point is the
`suzanne:connection-confirmed` event. It is emitted only after the OpenAI
remote description has been applied and the Realtime data channel is open. The
listening jingle plays only on the first Start press. Microphone tracks remain
muted until both the handshake and jingle finish; an audio error or bounded
timeout cannot prevent readiness. Reconnecting does not replay the jingle.

The browser posts its SDP offer to `POST /api/assistant/realtime/call`; the
backend sends SDP and the complete session configuration to OpenAI in one
request. No browser token request or full ICE-gathering wait is needed. The
legacy `/realtime/session` endpoint remains available for compatibility.

Server VAD detects and commits speech but `create_response` is false. The app
owns response creation, waits for both generation completion and speaker
playback completion, and serializes acknowledgements and tool-result speech.
Tool-only turns receive one short acknowledgement; pending tools cannot trigger
interim "still waiting" responses. Result and amenities narration use
`tool_choice: "none"`, so narration cannot launch a duplicate mutation.

## Route narration

Route planning may receive one short acknowledgement while the tool runs. The
returned deterministic result is spoken once and does not repeat the
acknowledgement or announce intermediate processing.

Route narration may use only returned facts:

- travel time, distance, requirements, and border facts;
- telemetry battery, range, consumption, maximum charged range, and charging
  feasibility;
- returned weather or severity alerts;
- verified partner benefits and route opportunities.

Missing facts are stated as unavailable. Suzanne never estimates range,
weather, pricing, availability, or charging feasibility.

## Place narration

Attractions and other Google Places results may include an optional summary,
photo reference, rating, review count, top keywords, provider, and source.
Suzanne may describe what can be seen or done only from the returned summary,
details, or keywords. Review counts and ratings are reported as facts; review
sentiment is never invented.

Search results are suggestions. They do not change the route until the driver
authorizes a reroute, booking, or other mutation.

## Charging and amenities

A confirmed charging response contains the complete ordered charging plan.
Suzanne names every returned stop and duration once, then states every verified
charging partner benefit. Nearby amenities are read-only and any verified
partner benefit is stated with its returned brand and exact benefit.

The voice layer must not describe only the first charger as the complete plan.

Chargers are added while the map stays in overview. The first stop is focused
only when its amenities speech starts and nearby results exist. Overview is
restored when that audio finishes. Interrupted speech cancels the automatic
continuation and restores overview; stale playback events cannot advance it.

## Vignette context

Compact route facts retain `routeRequirements` with exact ID, name, country,
and kind. Those IDs are operational context only and are never spoken or
requested from the driver. A clear purchase request supplies consent.

`requirementId` is optional on the purchase tool: the backend resolves a single
remaining vignette on the active route. Multiple remaining countries require a
country choice, not an internal ID. Explicit stale IDs and stale routes are
still rejected. Purchases return updated `sessionFacts`, remove purchased
requirements from future offers, and remain idempotent.

## Regression and live acceptance

Automated checks:

- `backend/.venv/Scripts/python.exe -m pytest tests/backend -q` (Windows).
- `npm test`, `npm run lint`, and `npm run build` in `frontend` (Node 22.18+).

Optional mounted-browser check: with the Vite server running, run
`node tests/realtimeHook.browser.mjs` from `frontend`. Set
`PLAYWRIGHT_MODULE_PATH` if Playwright is supplied by a bundled runtime rather
than installed locally. It uses installed Edge headlessly by default; override
`TEST_BROWSER_CHANNEL` for another installed Chromium channel. All tool calls
are mocked and it tests the real React hook, including charging focus timing.
Set `LIVE_REALTIME=1` to additionally test one real handshake against a backend
on port 8001; `TEST_FRONTEND_URL`/`TEST_BACKEND_URL` override test server URLs.
The live check uses synthetic microphone input, keeps its tracks muted, and
makes no Google calls. Provider credentials must be valid.

Live browser acceptance with the configured providers:

1. Start: jingle once, microphone muted until readiness. Stop and restart:
   no second jingle; old sessions cannot publish late results.
2. Request the fastest Budapest route: one acknowledgement, silence during
   processing, then one concise authoritative route/weather/requirements result.
3. Ask to buy the vignette: no ID question. Repeat the purchase: duplicate
   confirmation, not a second transaction. A country choice is required only
   when multiple vignette requirements remain.
4. Add charging: all necessary stops appear in overview, charger details finish,
   amenities speech focuses the first stop, and overview returns after playback.
   No amenities means no zoom. Interrupt amenities: no stale automatic zoom.
5. Search/choose attractions and book hotel/restaurant suggestions as before.
6. Inspect `realtime_connection_ms` in browser logs and `realtime_call_ms` on the
   backend. Compare cold and reconnect timings on the demo network. The structural
   reduction in startup requests is tested; real latency is not a fixed promise.
7. Verify the existing Google request budget: these voice changes add no Places,
   Routes, or Geocoding requests.

## Statement-first policy

### Concise action results

- Vignette purchase: acknowledge with "Got it." and report the purchase outcome
  once, followed by phone confirmation in the same sentence when the API returns
  `phoneConfirmationStatus: simulated_sent`. This flag models presentation-only
  delivery; it does not send a real notification or integrate with a phone app.
  Do not separately announce wallet completion. Repeated purchases report
  that the vignette was already purchased.
- Charging confirmation speaks station details and verified charging benefits
  once in overview. The zoomed amenities continuation mentions only nearby
  places and their own verified benefits, never another route summary.
  Compact route facts expose `chargingPlanReady`, stop count and the confirmation
  action without narrating unconfirmed stations. "Add charging" confirms all
  prepared necessary stops; fresh charger searches require an explicit search
  request. Short routes do not prefetch optional chargers or pretend one is ready.
- POI additions report the added place and the before/after driving-time delta,
  not the total route duration or weather. Visiting time is not included. Only
  newly changed requirements or returned charging feasibility may be mentioned.
- Hotel suggestions require Google review ratings strictly greater than 4.0/5.
  Missing scores and 4.0 are excluded before ranking, with at most two results.
  This is a review threshold, not an official hotel classification. Empty results
  do not trigger automatic extra provider searches or relaxed filtering.

Statements are the default for route results, telemetry, weather, prices,
requirements, partner facts, errors, and completed actions. Suzanne asks one
question only when explicit authorization or missing required booking details
are needed. An answered authorization question is never repeated.
