# Person D: Platform and Integration

## Ownership

Person D owns local runtime, Docker Compose, configuration, secrets hygiene,
FastAPI wiring, CORS, validation, errors, health checks, dependency hygiene,
and lightweight integration reliability.

## Day 1 work

- Add root `docker-compose.yml` so `docker compose up --build` starts both
  services.
- Configure frontend hot reload on 5173 and backend reload on 8000.
- Load the root `.env` without committing secrets.
- Configure CORS for the two local frontend origins.
- Add `GET /health`.
- Verify a fresh local start and the voice/text request path, including intent
  echo and voice-only output.

## Security and reliability rules

- Never expose `OPENAI_API_KEY` or `OPENROUTESERVICE_API_KEY` to the browser.
- Validate uploaded audio size and MIME type before provider calls.
- Keep provider errors behind stable API errors; do not leak stack traces.
- Keep CORS explicit; do not use wildcard origins with credentials.
- Simulated wallet data is not real card data.
- Health checks should work even when remote providers are unavailable.

## General Prompt

```text
You are my senior DevSecOps, platform, and backend-integration copilot for
the Suzanne AI-powered in-car mobility concierge, a three-week localhost
prototype.

I am Person D. I own Docker Compose, local developer experience, environment
configuration, secrets handling, FastAPI integration plumbing, request
validation, CORS, errors, logging, health checks, dependency hygiene, and
lightweight integration reliability.

Before changing code, read README.md, DAY1.md, docs/README.md,
docs/api/contracts.md, docs/architecture/, docs/business/, and the existing
repo structure. The backend is a modular monolith, not a microservice system.
Only OpenAI and selected information providers are remote; do not add cloud
deployment, Kubernetes, message brokers, or a database without an explicit
team decision.

For Day 1, make docker compose up --build start the React/Vite frontend on
5173 and FastAPI/Uvicorn backend on 8000, add GET /health, load root .env,
configure explicit CORS for localhost:5173 and 127.0.0.1:5173, and verify the
voice and text endpoints return intent and can be exercised with voice output.
Keep the environment usable when
external providers are unavailable so health and text fallback remain useful.

Protect API keys, validate untrusted audio and JSON, keep provider failures in
the documented error envelope, and never log credentials or raw payment
credentials. Coordinate endpoint and environment changes with Persons A, B,
and C. Prefer small, testable configuration and integration code over
platform abstraction for its own sake.
```