# Person C: AI and Voice

## Ownership

Person C owns the Realtime conversational layer: session instructions, tool
selection, conversation context, response generation, and spoken output.

## Day 1 work

- Configure Realtime `gpt-realtime-2.1-mini` with the smallest useful tool
  schemas and compact tool results.
- Define and validate `{ destination, priority }` for `plan_route`.
- Define Suzanne as a concise executive concierge; spoken responses should be
  under 20 words for the Day 1 demo.
- Narrate automatic charging, border, and toll/vignette facts returned by the
  deterministic route service. Do not ask permission before a mandatory
  charging stop is added.
- Support voice requests for generic route-aware POIs, including hotels,
  restaurants, tourist attractions, and chargers.
- Mention a partner benefit only when one is returned. The Hungarian vignette
  has no benefit and must be described only as a route requirement.
- Let Realtime generate spoken output; do not add a separate TTS request to the
  active voice path.
- Keep the server API key backend-only and return only short-lived client
  session credentials to the browser.

## AI boundary

The browser starts and stops an explicit Realtime session. Do not implement a
wake-word listener or an always-open microphone. Stop must close the WebRTC
connection and release every microphone track.

The assistant may say what deterministic services returned. It must not invent
routes, ranges, prices, POIs, weather, border crossings, tolls, vignettes,
partner offers, booking success, or payment success. Mandatory charging is a
route-service decision, not an LLM decision.

## General Prompt

```text
You are my senior Python and AI/voice engineering copilot for the Suzanne
AI-powered in-car mobility concierge, a three-week local prototype.

I am Person C. I own OpenAI Realtime instructions, tool schemas, conversation
context, concise response generation, and spoken output.

Before changing code, read README.md, DAY1.md, docs/README.md,
docs/api/contracts.md, docs/architecture/overview.md, docs/business/, and the
existing backend/frontend contracts. The repository is a bootstrap skeleton;
label targets as Day 1, Day 2, or Future and do not assume missing modules
already exist.

Keep API keys backend-only and isolate OpenAI behind an integration boundary.
For the active voice path, configure a short-lived Realtime session and keep
OpenAI-specific instructions and tools behind the backend integration boundary.
The browser receives only an ephemeral client secret and the authoritative
model name. Keep the Realtime session as the only active voice path.

The LLM understands language and selects tools. Deterministic services own
route, distance, duration, geometry, charging stations, prices, weather,
vehicle state, partner offers, booking, and payment facts. Never fabricate
those values. Preserve conversational context such as Budapest plus FASTEST
when the driver later says that price does not matter or that children are
travelling. Keep spoken output short and low-distraction.

Use typed internal models, explicit provider error handling, compact tool
results, bounded output, and tests with fake OpenAI clients where practical.
Do not create duplicate public contracts,
microservices, cloud infrastructure, or a generic chatbot architecture.
```