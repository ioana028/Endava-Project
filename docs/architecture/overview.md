# Architecture Overview

## Product boundary

Suzanne is a local modular monolith. One backend process exposes APIs and
coordinates deterministic domain services, local fixtures, and external
providers. One frontend process renders the in-car HMI. There are no
microservices, message brokers, cloud databases, Kubernetes resources, or
required cloud deployment targets.

```text
Browser / HMI
    |
    | Realtime WebRTC audio + JSON tool calls
    v
FastAPI modular monolith
    |
    +-- Assistant / AI integration
    +-- Trip and vehicle domain services
    +-- Partner and commerce boundaries
    +-- JSON fixture loaders
    +-- External provider adapters
```

## Technology choices

- Frontend: React 18, TypeScript, Vite, TailwindCSS, Google Maps JavaScript
  API, Lucide.
- Backend: Python 3.11+, FastAPI, Pydantic v2, Uvicorn, HTTPX.
- AI: OpenAI Realtime `gpt-realtime-2.1-mini` over browser WebRTC, with
  backend-owned deterministic tools. The browser uses an explicit Start/Stop
  session lifecycle; it does not use a wake word, MediaRecorder uploads, or a
  separate TTS step on the active path.
- Routing: Google Routes and Geocoding adapters plus a backend-only Places
  adapter for charging and generic route-aware POIs. Routes accepts selected
  waypoints; Places discovers candidates. Country/road rules remain
  deterministic application logic.
- Data: flat JSON fixtures under `data/`; no remote database.

## Core principle

The LLM understands and communicates. Deterministic code calculates facts.

The AI may:

- transcribe speech;
- extract destination and preferences;
- select a domain capability;
- maintain conversational context;
- turn returned facts into concise speech.

The active voice path begins only after the driver presses Start Suzanne. The
backend mints a short-lived Realtime client secret, the browser connects over
WebRTC, and Stop closes the peer connection and microphone tracks. Realtime
selects tools; deterministic backend services calculate every factual result.

The AI must not invent route geometry, distance, duration, charging stations,
prices, vehicle range, weather, partner offers, booking success, or payment
success.

## Suggested module layout

The existing directories are intentionally empty placeholders. Add code within
their existing ownership areas rather than creating parallel applications:

```text
backend/app/
  api/             FastAPI routes, request/response wiring
  core/            settings, logging, shared application dependencies
  integrations/    OpenAI, routing, weather, partner provider adapters
  models/          Pydantic/domain models
  services/        deterministic trip, vehicle, assistant, commerce logic
  utils/           small cross-cutting helpers
frontend/src/
  app/             application shell and providers
  components/      reusable UI
  features/        assistant, trip, map, vehicle, partners, commerce
  services/        HTTP client and browser integrations
  store/           UI/session state
  types/           shared frontend contracts
```

## Dependency direction

API routes should validate and delegate. They should not contain route scoring,
OpenAI prompt construction, or frontend-specific formatting.

```text
api -> services -> integrations / data
api -> models
frontend services -> api contracts
frontend features -> frontend services and types
```

Provider-specific response formats stop at integration adapters. Domain
services consume typed application models.

## Ownership

| Person | Primary question | Area |
|---|---|---|
| A | What does the driver see and how does it fit together? | Product, architecture, React/HMI, map |
| B | What is the best factual journey? | Trip, vehicle, range, stops, scoring |
| C | What does the driver mean and hear? | Realtime instructions, tools, context, spoken output |
| D | How does it run and connect reliably? | Runtime, API plumbing, config, CORS, security |

Ownership is not a silo. Shared contracts and architecture changes involve A;
the implementer owns tests for the behavior they add.