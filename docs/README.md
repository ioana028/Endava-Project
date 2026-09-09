# Suzanne Documentation

Suzanne is a voice-first, telemetry-aware in-car concierge for a luxury BEV.
The project is a local modular monolith built for a three-week presentation
prototype. This documentation is the shared working context for the team and
for coding AIs.

## Start here

1. Read [Project Scope](product/scope.md).
2. Read [Architecture Overview](architecture/overview.md).
3. Read [API Contracts](api/contracts.md).
4. Read the onboarding guide for the role you are implementing.
5. Read [Day 1 Walking Skeleton](product/day1-walking-skeleton.md) before
   changing the bootstrap plan.

## Documentation map

| Area | Contents |
|---|---|
| `api/` | HTTP payloads, shared types, validation, errors, and protocol rules |
| `architecture/` | System shape, module ownership, runtime, and integration boundaries |
| `business/` | Domain vocabulary, deterministic rules, and partner/commerce constraints |
| `onboarding/` | Role guidance and copy-pasteable AI General Prompts |
| `product/` | Scope, demo scenarios, priorities, and Day 1 acceptance criteria |

## Sources of truth

- `README.md` is the repository-level product and technology summary.
- `DAY1.md` is the current Day 1 delivery plan.
- `frontend/src/types/contracts.ts` is the canonical frontend TypeScript
  contract until a deliberate shared-contract change is agreed.
- `data/vehicles/telemetry.json` and `data/partners/partners.json` are the
  current demo fixtures.
- This documentation explains how those sources fit together. It must not
  silently redefine them.

## Current implementation status

The repository is a bootstrap skeleton. Backend routes, frontend application
files, Docker Compose, and AI integrations still need to be implemented.
Statements labelled `Day 1`, `Day 2`, or `Future` are targets, not claims that
the behavior already exists.

## Team rule

When changing a shared contract, module boundary, provider, or product scope,
update the relevant documentation and notify Person A before parallel work
continues.