# Day 7 Voice Flows

This document freezes Person C's Realtime voice contract for partner facts,
scenic routing, and presentation-only driving mode.

## Route and scenic preference

```text
Driver: Take the scenic route to Budapest.
Suzanne: I will use scenic routing as a preference and compare the available route facts.
Suzanne: The scenic option is an estimate based on the returned route data; I cannot promise views or road quality.
```

`SCENIC` is preserved exactly in the `plan_route` tool request. Suzanne may
call the result scenic only when the returned facts support that description.
Provider or offline fallback limitations must not be hidden, and scenic mode
must never be described as a guaranteed view, landscape, or road condition.

## Partner discovery

```text
Driver: Find a hotel near Budapest.
Suzanne: I found the Riverside Hotel, rated 4.5, with free breakfast for partner customers.
```

Suzanne may mention a partner only when the returned compact facts include the
partner identity and a concrete benefit. A category, provider brand, rating,
detour, vignette requirement, or generic partner flag is not a benefit.

```text
Driver: Find a restaurant along the route.
Suzanne: I found a restaurant along the route.
```

When no explicit benefit is returned, Suzanne must not add a discount, free
item, loyalty claim, or other commercial statement.

## Start driving

```text
Driver: Let's get going.
Suzanne: Driving mode is active. You have 184 kilometres and about 2 hours 41 minutes remaining; your next stop is ChargePoint Parndorf.
```

`start_driving` requires the current `routeId` and exact
`confirmation: "confirmed"`. The response preserves that route ID and contains
only compact progress, ETA, next-stop, and charging facts. It activates the
presentation-only driving state and does not replan or call the route provider.

## Tool result speech

Every successful tool result receives one concise spoken response that states
completion and the returned facts. A brief acknowledgement may be used while
the tool runs, but it must not be repeated after the result.

Every failed tool result receives one clear, actionable spoken error based on
the returned stable error code and message. A failed tool must never leave the
driver with silence.

Examples:

```text
Suzanne: I could not use that route because the route context is no longer current. Please plan the route again.
Suzanne: The nearby search is unavailable right now. You can try again in a moment.
```

## Context and payload safety

- Preserve the exact `routeId`, `searchId`, and selected result IDs returned by tools.
- Reject stale route, stop, search, or result context with the stable error envelope.
- Keep route geometry and raw provider payloads out of Realtime messages.
- Do not invent duration, distance, charging, availability, ratings, benefits, or scenic claims.
