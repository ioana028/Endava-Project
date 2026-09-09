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
    | HTTP and multipart voice upload
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

- Frontend: React 18, TypeScript, Vite, TailwindCSS, MapLibre GL, Lucide.
- Backend: Python 3.11+, FastAPI, Pydantic v2, Uvicorn, HTTPX.
- AI: OpenAI Whisper `whisper-1`, tool calling/structured output, and TTS
  `tts-1` with the `nova` voice for the Day 1 demo.
- Routing and POIs: OpenRouteService adapter, to be implemented after the
  walking skeleton.
- Data: flat JSON fixtures under `data/`; no remote database.

## Core principle

The LLM understands and communicates. Deterministic code calculates facts.

The AI may:

- transcribe speech;
- extract destination and preferences;
- select a domain capability;
- maintain conversational context;
- turn returned facts into concise speech.

On Day 1, the AI returns the extracted intent to the backend, and the backend
returns that intent to the frontend. The frontend then plays the fixed voice
response `Calculating route based on your preferences, hold on`. No route is
calculated on Day 1.

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
| C | What does the driver mean and hear? | Whisper, intent, tools, context, TTS |
| D | How does it run and connect reliably? | Runtime, API plumbing, config, CORS, security |

Ownership is not a silo. Shared contracts and architecture changes involve A;
the implementer owns tests for the behavior they add.