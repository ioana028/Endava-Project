# Parallel Work Rules

## Safe parallel surfaces

- A can build HMI components against `contracts.ts` and mocked responses,
  showing the returned intent as read-only state and playing voice output.
- B can build typed deterministic trip services against fixture interfaces.
- C can build AI adapters and internal intent models behind service interfaces.
- D can build settings, health, CORS, Compose, and API error handling.

Each person should keep provider calls behind an interface so another person
can use a fake implementation in tests.

## Shared surfaces

Discuss changes before merging when they affect:

- `frontend/src/types/contracts.ts`;
- `docs/api/contracts.md`;
- endpoint paths or response envelopes;
- coordinate order or units;
- route/stops/alerts enum values;
- environment variable names;
- product scope or provider choice.

## Integration sequence

1. Agree on request and response shapes.
2. Implement service interfaces and fake data paths.
3. Add focused unit tests.
4. Integrate through FastAPI and the frontend API client.
5. Run the walking-skeleton acceptance flow.

The Day 1 acceptance flow has no confirmation button. A confirmation or
holding response is delivered through Suzanne's voice only.

Do not block UI work on a live external provider. Do not merge a provider
response directly into the browser without mapping it to the canonical model.