# Onboarding

Read the role guide that matches your primary ownership, then read the shared
[General Prompt](#shared-context-for-every-ai). Each role guide contains a
role-specific General Prompt that can be pasted into an AI coding session.

## Shared context for every AI

Every AI working in this repository should:

- read `README.md`, `DAY1.md`, `docs/README.md`, and the relevant contract
  before editing;
- treat `frontend/src/types/contracts.ts` as canonical frontend vocabulary;
- preserve the local modular-monolith architecture;
- avoid duplicate models, microservices, cloud infrastructure, and speculative
  abstractions;
- keep deterministic facts out of LLM-generated guesses;
- treat Day 1 as voice input -> intent -> backend response -> voice output;
- never add on-screen confirmation buttons; confirmations are spoken;
- add tests for behavior owned by the change;
- say clearly when a requested behavior is Day 2 or Future rather than
  pretending it already exists;
- update documentation when changing a shared boundary.

## Role guides

- [Person A: Frontend](PERSON_A_FRONTEND.md)
- [Person B: Backend](PERSON_B_BACKEND.md)
- [Person C: AI and Voice](PERSON_C_AI.md)
- [Person D: Platform](PERSON_D_PLATFORM.md)