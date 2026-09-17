# Day 6 Voice Flows

This document is the executable conversation contract for Person C's Realtime
tools. Commerce and bookings are simulations only.

## Vignette purchase

```text
Driver: Can you purchase the vignette for me, please?
Suzanne: Done. I completed the simulated purchase using the in-car wallet and
         prepared confirmation for your phone app.
```

The tool requires the current `routeId`, returned `requirementId`, and exact
`confirmation: "confirmed"`. Without a current requirement, return
`MISSING_REQUIREMENT` and do not create a transaction.

## Hotel booking

```text
Driver: Find me a hotel near Budapest.
Suzanne: Returns factual hotel suggestions.
Driver: The Riverside Hotel looks good.
Suzanne: Stores the selected result and asks for missing booking details.
Driver: Book a room for 2.
Suzanne: Done. I completed the simulated hotel booking through the in-car
         wallet and prepared confirmation for your phone app.
```

Selecting, naming, or praising a hotel never books it. The booking preserves
the exact `routeId`, `searchId`, and `resultId` from the active search.

## Restaurant booking

```text
Driver: Find a restaurant near Budapest.
Suzanne: Returns factual restaurant suggestions.
Driver: Book a table for 2 at the first one.
Suzanne: Done. I completed the simulated restaurant booking through the
         in-car wallet and prepared confirmation for your phone app.
```

Hotel bookings use `hotel_room`; restaurant bookings use
`restaurant_table`. Both require explicit confirmation. Missing date, time, or
guest details must be requested or supplied only by a documented deterministic
demo default.

## Driving mode

```text
Driver: Let's get going.
Suzanne: We are ready to go. Driving mode is active.
```

`start_driving` requires the current `routeId` and exact confirmation. It
returns only compact progress facts and must not replan or mutate route
geometry.

## Return to the main route

```text
Driver: Okay, let's get back to the main route.
Frontend: Restores the route-wide presentation without replanning.
```

`return_to_main_route` preserves the current route ID and clears only the
charger-focused amenity presentation.

## Error and safety flows

- Stale route, search, or result context returns a structured 409 error.
- Missing or non-exact confirmation returns structured 422 `VALIDATION_ERROR`.
- Duplicate actions return the existing transaction or booking, or a duplicate
  status, and never create a second result.
- Missing details return `MISSING_DETAILS` without booking.
- Unavailable downstream services return structured 503 errors.
- Realtime responses contain compact status facts only, never credentials,
  payment data, audio, or raw provider payloads.