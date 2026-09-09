# Product Scope

## Vision

Suzanne is an AI-powered, voice-first in-car smart route planner for a luxury
BEV. It combines vehicle telemetry, deterministic trip intelligence,
conversational AI, route-aware POI discovery, and an optional OEM partner
marketplace in one believable HMI.

The product should demonstrate:

```text
understand -> plan -> adapt -> recommend -> book/pay (simulated)
```

## In scope

- Local React HMI with microphone, assistant state, map, route cards, alerts,
  and audio playback.
- Local FastAPI modular monolith.
- Destination and route-style planning for fastest, scenic, cheapest, and
    balanced journeys.
- BEV telemetry and range-aware mandatory charging recommendations.
- Route-aware toll, vignette, and border requirements.
- Weather alerts along the planned route.
- Generic POI discovery for food, coffee, rest, toilets, and other stops even
    when no partner is available.
- Vienna to Budapest demo corridor.
- OpenAI STT, structured intent/tool calling, and TTS.
- OpenRouteService adapter for future route and POI data.
- Flat JSON fixtures for demo vehicle and partners.
- Optional partner suggestions and discounts with explicit voice consent; no
    on-screen confirmation buttons.
- Simulated vignette, booking, and wallet confirmation flows.

## Out of scope

- Real card processing or financial transactions.
- Raw payment-card storage.
- Real OEM/CAN vehicle integration.
- Production authentication or production-scale infrastructure.
- Microservices, Kubernetes, message brokers, or a remote application DB.
- Europe-wide complete POI coverage.
- Autonomous driving and production predictive maintenance.

## Priority rule

Prefer work that improves a documented demo scenario, correctness of the
LLM/deterministic boundary, local reliability, or presentation clarity within
three weeks. Do not build generic systems that do not advance the demo.