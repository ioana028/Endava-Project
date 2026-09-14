# Person A: Frontend and Voice HMI

## Ownership

Person A owns product direction, architecture, React/TypeScript, the
infotainment HMI, map rendering, assistant states, and presentation polish.
The first target is a reliable 2D walking skeleton; the 3D cockpit comes
later.

## Active Realtime work

- Set up React 18, Vite, TypeScript, and TailwindCSS on port 5173.
- Build explicit `Start Suzanne` and `Stop Suzanne` controls with
  `CONNECTING`, `LISTENING`, `PROCESSING`, `SPEAKING`, and `ERROR` states.
- Request microphone permission only after Start and connect over WebRTC using
  the short-lived backend client secret.
- Close the peer connection and stop every microphone track on Stop.
- Forward only Realtime tool arguments to the backend and keep full route data
  local for the map and route summary.
- Send only compact narration facts back to Realtime; never send geometry.
- Use the active Realtime WebRTC path for route requests and tool calls.
- Day 3 renders the final route after automatic charging, shows border
  crossings and toll/vignette requirements, and distinguishes driving time
  from total time including charging.
- Day 3 supports voice-driven generic POI results for charging, hotels,
  restaurants, and attractions without selectors or confirmation cards.

## Frontend rules

- Reuse `frontend/src/types/contracts.ts`; do not create a parallel response
  type.
- Treat `route` as optional and handle `undefined` and `null` during Day 1.
- Treat `intent` as the Day 1 result; it is not a route confirmation.
- Do not parse `spokenResponse` to infer route state.
- Do not create confirmation buttons; all confirmations are spoken.
- Release media tracks and old audio URLs after use.
- Do not send the server OpenAI credential to the browser. Browser audio may go
  directly to OpenAI only through the user-started ephemeral WebRTC session.
- Keep controls usable on desktop and mobile widths.
- Never show the Hungarian vignette as a partner benefit; render only an
  optional benefit supplied by the structured contract.

## General Prompt

```text
You are my senior frontend and product engineering copilot for the Suzanne
AI-powered in-car mobility concierge, a three-week local prototype.

I am Person A: Team Lead, Solution Architect, product/UX owner, and primary
React/TypeScript engineer. I own the infotainment HMI, microphone interaction,
audio playback, map and route visualization, assistant states, partner and
commerce UI, shared architecture, and final presentation polish.

Before changing code, read README.md, DAY1.md, docs/README.md,
docs/api/contracts.md, relevant architecture docs, and
frontend/src/types/contracts.ts. Treat contracts.ts as the canonical frontend
contract. The repository is currently a bootstrap skeleton, so distinguish
implemented behavior from Day 1, Day 2, and Future targets.

Preserve the local React frontend plus FastAPI modular monolith. Do not add
microservices, cloud infrastructure, duplicate contracts, or unnecessary
dependencies. The LLM may interpret language, but it must not invent route,
vehicle, price, weather, POI, partner, booking, or payment facts. The frontend
must consume structured backend responses and never parse speech to decide UI
state.

For the active path, prioritize explicit Start/Stop controls, the Realtime
WebRTC lifecycle, compact tool payloads, structured route rendering, and clear
connection errors. Do not add on-screen confirmation buttons or a wake-word
listener. Add focused tests or a repeatable verification step for behavior you
change. If a shared contract or architecture decision must change, explain the
impact and update the relevant documentation.
```