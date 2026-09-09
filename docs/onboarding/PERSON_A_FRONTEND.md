# Person A: Frontend and Voice HMI

## Ownership

Person A owns product direction, architecture, React/TypeScript, the
infotainment HMI, map rendering, assistant states, and presentation polish.
The first target is a reliable 2D walking skeleton; the 3D cockpit comes
later.

## Day 1 work

- Set up React 18, Vite, TypeScript, and TailwindCSS on port 5173.
- Build the microphone button with `IDLE`, `LISTENING`, `PROCESSING`, and
  `SPEAKING` states.
- Capture browser audio with `MediaRecorder` after explicit permission.
- Send the recording as `audio` to `POST /api/assistant/voice`.
- Render the returned intent as read-only information and play returned
  `audioBase64` through `HTMLAudioElement`.
- Keep a text fallback for `POST /api/assistant/interact`.

## Frontend rules

- Reuse `frontend/src/types/contracts.ts`; do not create a parallel response
  type.
- Treat `route` as optional and handle `undefined` and `null` during Day 1.
- Treat `intent` as the Day 1 result; it is not a route confirmation.
- Do not parse `spokenResponse` to infer route state.
- Do not create confirmation buttons; all confirmations are spoken.
- Release media tracks and old audio URLs after use.
- Do not send OpenAI credentials or audio directly to OpenAI.
- Keep controls usable on desktop and mobile widths.

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

For Day 1, prioritize the four assistant states, MediaRecorder capture,
POST /api/assistant/voice, POST /api/assistant/interact, returning the
extracted intent to the UI, base64 MP3 playback of the exact phrase
"Calculating route based on your preferences, hold on", and clear errors. Do
not add on-screen confirmation buttons. Add focused tests
or a repeatable verification step for behavior you change. If a shared
contract or architecture decision must change, explain the impact and update
the relevant documentation.
```