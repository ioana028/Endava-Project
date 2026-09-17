# Day 6: Simulated Commerce, Bookings, Performance, and Driving Mode

## Purpose

Day 6 extends the working Day 5 route assistant with fully simulated commerce,
booking, performance improvements, and a driving-mode transition. No real
payment, government, hotel, or restaurant transaction is performed.

Day 6 does not add `sessionStorage`. Refreshing the browser resets the complete
session. Stopping Suzanne disconnects voice but keeps the current route, stops,
POIs, and simulated action results until refresh or a new route is planned.

## Product outcomes

At the end of Day 6:

- Suzanne can simulate purchasing a returned vignette requirement.
- The simulated purchase uses the in-car wallet and creates a transaction
  reference plus a phone-app confirmation state.
- Suzanne can search for hotels and restaurants using the existing POI flow.
- The driver can select a result and request a simulated hotel room or
  restaurant table booking.
- Hotel bookings support `book a room for 2`.
- Restaurant bookings support `book a table for 2`.
- Selecting or praising a result alone never books it.
- A clear purchase or booking request authorizes the simulation.
- Duplicate and stale actions are rejected or return the existing result.
- Suzanne startup and route planning expose timing data and are faster than the
  Day 5 baseline.
- `Let's get going`, `Start driving`, and equivalent language activate driving
  mode.
- `Okay, let's get back to the main route` exits the charger-focused amenity
  view without replanning or refetching the route.
- Returning to the main route restores the route-wide camera and allows new
  attraction, hotel, restaurant, and other POI searches on the same route.
- Driving mode shows route progress, remaining distance, remaining duration,
  destination, next relevant stop, charging status, and ETA.
- Long routes receive as many mandatory charging stops as the vehicle range
  and route distance require. A route is not limited to one charger when one
  stop cannot make the journey safe.
- When driving mode starts, the trip information utility panel switches back to
  the music panel. Driving information remains visible in the map/navigation
  surface and driving status area.
- After a successful simulated purchase or booking, the Suzanne card visibly
  transforms into a checkmark for a few seconds and then returns to normal.
- Browser refresh resets route, voice, navigation, bookings, purchases, and
  commerce state.
- No two people edit the same implementation file.

## Golden flow

```text
Driver: Take me to Budapest.
Suzanne: Plans the route and reports the returned route facts and vignette requirement.
Driver: Can you purchase the vignette for me, please?
Suzanne: Completes the simulated wallet purchase.
Suzanne: Done, I prepared confirmation for your phone app.
Driver: Find me a hotel near Budapest.
Suzanne: Returns a few factual hotel results.
Driver: The Riverside Hotel looks good.
Suzanne: Stores the selection and asks for missing booking details.
Driver: Can you book a room for 2?
Suzanne: Completes the simulated hotel booking through the in-car wallet.
Suzanne: Done, I booked it and prepared confirmation for your phone app.
Driver: Let's get going.
Frontend: Activates driving mode and switches the trip panel back to music.
Driver: Okay, let's get back to the main route.
Frontend: Restores the full-route camera without replanning or refetching.
Driver: What tourist spots can we see along the route?
Suzanne: Searches the existing route context rather than starting over.
```

## Architecture rules

- Commerce and bookings are simulated only. Do not call Stripe, government,
  hotel, restaurant, or other live transaction providers.
- The simulated wallet is backend-owned. Browser and Realtime responses contain
  compact status facts only, never credentials or card data.
- Suzanne must say that an action was simulated through the in-car wallet. She
  must not claim a real purchase, real booking, real payment, or real phone
  notification.
- A purchase requires a current route requirement. A booking requires a current
  selected provider result and valid route/search context.
- Hotel and restaurant booking types remain distinct: `hotel_room` and
  `restaurant_table`.
- Missing date, time, or guest details must be requested, or supplied only from
  a documented deterministic demo default.
- Repeating the same action with the same request key is idempotent.
- Driving mode changes camera and presentation state only; it never mutates
  route geometry or adds a stop.
- Returning to the main route is a camera/presentation change only. It must not
  call route planning, replace the route, or create a new route ID.
- Charging-stop planning is deterministic and may select multiple reachable
  stops. Each selected stop is justified by route progress, range, safety
  buffer, compatibility, availability, and provider facts.
- Never invent turn-by-turn instructions from a polyline. Use provider steps
  when available; otherwise show simulated progress facts only.
- Raw provider payloads never enter Realtime messages or browser state.
- Automated tests never call live Google, OpenAI, payment, hotel, or restaurant
  services.
- No `sessionStorage` is part of Day 6.

## Roles and ownership

### Person A: driving HMI, confirmation visuals, and browser acceptance

**Owns only:**

- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/features/map/**`
- `frontend/src/features/navigation/**`
- `frontend/src/features/commerce/components/**`
- `frontend/src/features/assistant/components/AssistantStatus.tsx`
- `frontend/src/features/trip/components/RouteSummary.tsx`
- `frontend/src/assets/**`
- `tests/frontend/**`
- `tests/e2e/frontend/**`

**Delivers:**

- Driving presentation state consuming Person C's contract.
- Close route-following camera, route emphasis, destination, next stop,
  remaining distance/duration, ETA, and charging status.
- The trip information utility panel switches back to the music panel when
  driving mode starts.
- Driving facts remain visible in a map/navigation surface.
- A `return_to_main_route` camera action restores full-route bounds, clears only
  the charger-focused amenity presentation, and preserves route context.
- Visible wallet, booking, and phone-confirmation status surfaces.
- Suzanne card success animation/checkmark for a short accessible duration.
- Pending, success, duplicate, stale, and failure visual states.
- Keyboard-accessible purchase and booking controls.
- Browser tests for refresh reset, driving transition, music restoration,
  purchase confirmation, and booking confirmation.

**Must not edit:** backend files, shared contracts, Realtime tools, provider
adapters, partner fixtures, or wallet/commerce services.

### Person B: deterministic commerce, booking, wallet, and route policy

**Owns only:**

- `backend/app/services/commerce/**`
- `backend/app/services/wallet/**`
- `backend/app/services/trip/service.py` only for Day 6 route-state helpers
- `backend/app/services/trip/deterministic.py` only for Day 6 route-state helpers
- `backend/app/services/recommendation/poi.py` only for booking eligibility
- `data/commerce/**`
- `tests/backend/unit/test_day6_commerce.py`
- `tests/backend/unit/test_day6_wallet.py`
- `tests/backend/unit/test_route_service.py` only for Day 6 changes

**Delivers:**

- Simulated wallet with `READY`, `PROCESSING`, `COMPLETED`, `DECLINED`, and
  `DUPLICATE` states.
- Simulated vignette purchase for a returned route requirement.
- Simulated hotel room and restaurant table bookings.
- Stable transaction IDs and booking confirmation codes.
- Phone confirmation states `PENDING`, `SENT`, and `FAILED`.
- Idempotent request keys.
- Validation for route ID, requirement ID, result ID, search ID, booking type,
  guest count, date, and time.
- Deterministic remaining distance, route progress, next stop, and ETA facts.
- Iterative multi-stop charging selection for long routes, including remaining
  range calculation after every selected stop.
- Stable mandatory charging-stop ordering by route progress.
- A clear no-safe-charging-plan failure when enough compatible reachable stops
  cannot be found.
- Tests proving selection or search alone cannot create a transaction or booking.

**Must not edit:** frontend files, Realtime/API wiring, shared contracts,
provider adapters, or partner JSON.

### Person C: Suzanne tools, orchestration, and shared contracts

**Owns only:**

- `backend/app/integrations/openai/realtime.py`
- `backend/app/api/assistant.py`
- `backend/app/models/contracts.py`
- `frontend/src/services/realtimeAssistantApi.ts`
- `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts`
- `frontend/src/types/contracts.ts`
- `tests/backend/integration/test_realtime_api.py`
- `tests/backend/unit/test_openai_realtime.py`
- `docs/api/day6-voice-flows.md`

**Delivers these tools:**

- `purchase_vignette`
- `book_hotel_room`
- `book_restaurant_table`
- `start_driving`
- `return_to_main_route`

The purchase request contains `routeId`, `requirementId`, and
`confirmation: "confirmed"`. Booking requests contain `routeId`, `searchId`,
selected `resultId`, booking type, guest count, date/time, and confirmation.
Driving requests contain the current route ID and return compact navigation
facts.

Suzanne understands:

- `Can you purchase the vignette for me, please?`
- `Please buy the vignette.`
- `Find me a hotel.`
- `Book a room for 2.`
- `Book a table for 2.`
- `Let's get going.`
- `Start driving.`
- `Okay, let's get back to the main route.`
- `Show me the full route again.`
- `Continue looking along the route.`

Expected simulated responses:

```text
Done. I completed the simulated vignette purchase using the in-car wallet and
prepared confirmation for your phone app.
```

```text
Done. I completed the simulated hotel booking for two using the in-car wallet
and prepared confirmation for your phone app.
```

```text
We are ready to go. Driving mode is active.
```

The hook exposes purchase, booking, phone-confirmation, driving, and timing
states. Stopping Suzanne does not erase the current route. A new route clears
stale POI, amenity, purchase, booking, and navigation context.

**Must not edit:** Person A visual components/CSS, Person B commerce/wallet
implementation, Person D provider/runtime files, partner JSON, or map internals.

### Person D: provider/runtime performance and navigation data

**Owns only:**

- `backend/app/integrations/places/google.py`
- `backend/app/integrations/places/provider.py`
- `backend/app/integrations/google_maps/routing.py`
- `backend/app/main.py`
- `backend/app/core/settings.py`
- `backend/app/core/errors.py`
- `.env.example`
- `docker-compose.yml`
- `docs/architecture/runtime.md`
- `docs/configuration/day6-runtime.md`
- `tests/backend/unit/test_google_integrations.py`
- `tests/backend/unit/test_day6_performance.py`

**Delivers:**

- Timing spans for session secret, microphone, peer connection, data channel,
  assistant ready, geocoding, route provider, charging lookup, total route
  planning, and tool calls.
- No credentials, raw provider payloads, audio, or secrets in timing logs.
- Bounded route sampling, safe caching/deduplication, and parallel independent
  work where it reduces route latency.
- Provider-neutral navigation steps when available:
  instruction, distance,
  duration, maneuver, and coordinates.
- Offline/google/auto provider behavior and safe timeout/quota diagnostics.

**Must not edit:** commerce/wallet services, Realtime tools/prompts, shared
contracts, frontend components, frontend hook/API files, partner JSON, or trip
ranking.

## Frozen shared contract examples

Person C freezes the contract before branch work is merged. JSON at the
HTTP/Realtime boundary uses camelCase.

### Simulated vignette purchase

```json
{
  "routeId": "route-123",
  "requirementId": "hu-vignette-10d",
  "confirmation": "confirmed"
}
```

```json
{
  "status": "completed",
  "transactionId": "txn-vignette-001",
  "routeId": "route-123",
  "requirementId": "hu-vignette-10d",
  "walletStatus": "completed",
  "phoneConfirmationStatus": "sent",
  "amountEur": 16.5,
  "currency": "EUR"
}
```

### Simulated hotel booking

```json
{
  "routeId": "route-123",
  "searchId": "search-456",
  "resultId": "hotel-riverside",
  "bookingType": "hotel_room",
  "guests": 2,
  "date": "2026-09-17",
  "confirmation": "confirmed"
}
```

### Simulated restaurant booking

```json
{
  "routeId": "route-123",
  "searchId": "search-456",
  "resultId": "restaurant-italia",
  "bookingType": "restaurant_table",
  "guests": 2,
  "date": "2026-09-17",
  "time": "19:00",
  "confirmation": "confirmed"
}
```

### Driving mode

```json
{
  "status": "active",
  "routeId": "route-123",
  "remainingDistanceKm": 184,
  "remainingDurationMinutes": 161,
  "eta": "14:35",
  "nextStop": {
    "id": "place-tea-mosonmagyarovar",
    "name": "TEA Mosonmagyarovar",
    "category": "charging"
  },
  "chargingRequired": true
}
```

## Voice flows

Person C writes the executable conversation contract in
`docs/api/day6-voice-flows.md`.

### Vignette

```text
Driver: Can you purchase the vignette for me, please?
Suzanne: Done. I completed the simulated purchase using the in-car wallet and
         prepared confirmation for your phone app.
Frontend: The Suzanne card becomes a checkmark for a few seconds.
Frontend: Wallet and phone confirmation states are visible.
```

Without a current returned requirement:

```text
I do not have a current vignette requirement to purchase.
```

### Hotel

```text
Driver: Find me a hotel near Budapest.
Suzanne: Returns factual hotel results.
Driver: The Riverside Hotel looks good.
Suzanne: What date and how many guests?
Driver: Can you book a room for 2?
Suzanne: Done. I completed the simulated booking through the in-car wallet and
         prepared confirmation for your phone app.
```

### Restaurant

```text
Driver: Find a restaurant near Budapest.
Suzanne: Returns factual restaurant results.
Driver: Book a table for 2 at the first one.
Suzanne: Done. I completed the simulated restaurant booking through the in-car
         wallet and prepared confirmation for your phone app.
```

### Driving

```text
Driver: Let's get going.
Suzanne: We are ready to go. Driving mode is active.
Frontend: Map switches to driving camera.
Frontend: Trip information panel switches back to music.
Frontend: Driving status remains visible on the map/navigation surface.
```

### Return to main route

```text
Driver: Are there amenities near the charger?
Frontend: Zooms to the selected charger and shows nearby results.
Driver: Okay, let's get back to the main route.
Frontend: Restores the route-wide camera without calling plan_route.
Driver: Find tourist spots along the route.
Suzanne: Searches the existing route and preserves the route ID.
```

### Multiple charging stops

For a route longer than the vehicle can safely complete with one charge:

```text
Suzanne: This route requires two charging stops: TEA Mosonmagyarovar and
         ChargePoint Parndorf. Both are reachable in sequence.
```

The backend must select stops iteratively by route progress. It must not return
only the first reachable charger when the remaining route still exceeds the
vehicle's safe range after that stop.

## Performance targets

Person D records:

- `session_secret_request_ms`
- `microphone_permission_ms`
- `peer_connection_ms`
- `data_channel_open_ms`
- `assistant_ready_ms`
- `geocode_ms`
- `route_provider_ms`
- `charging_lookup_ms`
- `total_route_plan_ms`
- `tool_call_ms`

Local demo targets:

- Suzanne ready: p50 under 2 seconds after start;
- core offline route facts: p50 under 3 seconds;
- no unbounded provider request fan-out;
- timing logs contain no secrets, raw provider data, audio, or credentials.

## Driving mode behavior

Driving mode is a presentation state over the current route, not a new route
calculation. It keeps route geometry, destination, charging stop, and stops.
It changes the camera to a closer route-following view and shows remaining
distance, remaining duration, ETA, next stop, and charging status.

It must switch the trip information utility panel back to the music panel. It
must not invent turn instructions from a polyline. Provider steps may be shown
when available; otherwise the UI shows simulated progress facts only.

## Confirmation visuals

Each successful simulated action has both:

1. a wallet/booking status surface with action, status, reference, and phone-app
   confirmation state;
2. an accessible Suzanne checkmark state lasting a few seconds, followed by the
   normal Suzanne card.

The checkmark includes an accessible text label and `aria-live` announcement.
Its timer is cleared when a new action starts or the component unmounts, and it
respects reduced-motion preferences.

## File ownership matrix

| File or area | Owner | Other people may review | Other people may edit |
|---|---|---|---|
| `frontend/src/App.tsx` | Person A | B/C/D | No |
| `frontend/src/index.css` | Person A | B/C/D | No |
| `frontend/src/features/map/**` | Person A | B/C/D | No |
| `frontend/src/features/navigation/**` | Person A | B/C/D | No |
| `frontend/src/features/commerce/components/**` | Person A | B/C/D | No |
| `frontend/src/features/assistant/hooks/useRealtimeAssistant.ts` | Person C | A/B/D | No |
| `frontend/src/services/realtimeAssistantApi.ts` | Person C | A/B/D | No |
| `frontend/src/types/contracts.ts` | Person C | A/B/D | No |
| `backend/app/models/contracts.py` | Person C | A/B/D | No |
| `backend/app/api/assistant.py` | Person C | A/B/D | No |
| `backend/app/integrations/openai/realtime.py` | Person C | A/B/D | No |
| `backend/app/services/commerce/**` | Person B | A/C/D | No |
| `backend/app/services/wallet/**` | Person B | A/C/D | No |
| `backend/app/services/trip/**` | Person B | A/C/D | No |
| `data/commerce/**` | Person B | A/C/D | No |
| `backend/app/integrations/places/**` | Person D | A/B/C | No |
| `backend/app/integrations/google_maps/**` | Person D | A/B/C | No |
| `backend/app/main.py` | Person D | A/B/C | No |
| `backend/app/core/settings.py` | Person D | A/B/C | No |
| `backend/app/core/errors.py` | Person D | A/B/C | No |
| `.env.example` | Person D | A/B/C | No |
| `docker-compose.yml` | Person D | A/B/C | No |
| `docs/architecture/runtime.md` | Person D | A/B/C | No |
| `docs/configuration/day6-runtime.md` | Person D | A/B/C | No |
| `tests/backend/unit/test_day6_commerce.py` | Person B | A/C/D | No |
| `tests/backend/unit/test_day6_wallet.py` | Person B | A/C/D | No |
| `tests/backend/unit/test_day6_performance.py` | Person D | A/B/C | No |
| `tests/backend/integration/test_realtime_api.py` | Person C | A/B/D | No |
| `tests/backend/unit/test_openai_realtime.py` | Person C | A/B/D | No |
| `tests/frontend/**` | Person A | B/C/D | No |
| `tests/e2e/frontend/**` | Person A | B/C/D | No |
| `docs/api/day6-voice-flows.md` | Person C | A/B/D | No |
| `day6.md` | Integration lead | A/B/C/D | No |

No Day 6 task may assign the same implementation file to two people. Person C
freezes shared contracts before branch integration. `App.tsx`, the Realtime
hook, and backend contract files remain single-owner surfaces.

## Branch and handoff protocol

Create `integration/day6` from the validated Day 5 integration commit:

```text
integration/day6
|-- person-a/day6-driving-hmi
|-- person-b/day6-simulated-commerce
|-- person-c/day6-suzanne-tools
`-- person-d/day6-performance-runtime
```

Rules:

1. Each person edits only owned files.
2. Person C freezes shared contracts before implementation merges.
3. Person B publishes wallet/booking examples before Person C writes tools.
4. Person D publishes timing names and navigation assumptions before Person A
   implements driving presentation.
5. Every branch includes tests for owned behavior.
6. Every branch includes a handoff note.
7. Do not rebase, squash, or force-push another contributor's work.
8. Conflicts return to the owner instead of being repaired by another owner.
9. The integration branch is not pushed to `main` until the complete gate passes.

Required handoff note:

```text
Owned files:
Day 6 requirements covered:
Contract assumptions:
Timing/UX assumptions:
Tests run:
Manual checks still needed:
Known limitations:
```

## Integration validation gate

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest tests/backend -q
Set-Location frontend
npm run build
npm run lint
Set-Location ..
git diff --check
git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- .
```

Acceptance must verify:

- vignette purchase requires a current requirement;
- repeated purchase requests are idempotent;
- hotel room booking works for two guests;
- restaurant table booking works for two guests;
- selection alone does not book or purchase;
- wallet and phone confirmation states are visible;
- Suzanne becomes an accessible checkmark for a few seconds;
- `Let's get going` activates driving mode;
- `Okay, let's get back to the main route` restores the full-route camera
  without calling route planning or changing the route ID;
- POI searches after returning to the main route use the existing route context;
- long routes receive multiple mandatory charging stops when required;
- charging stops are ordered by route progress and each is reachable in turn;
- the trip information panel switches back to music;
- route geometry is unchanged by driving mode;
- refresh returns to the origin-only state;
- stopping Suzanne does not erase the current route during the same page session;
- timing logs contain no secrets or raw provider payloads;
- all handoff notes are present and no ownership overlaps exist.

## Definition of done

Day 6 is complete only when simulated commerce, simulated bookings,
performance instrumentation, and driving mode are implemented and tested;
Suzanne can purchase a returned vignette and book a selected hotel or
restaurant; successful actions show wallet/phone confirmation and a temporary
Suzanne checkmark; `Let's get going` changes the map to driving mode and the
trip panel back to music; refresh intentionally resets the session; backend
and frontend gates pass; and the golden flow is accepted on `integration/day6`.
