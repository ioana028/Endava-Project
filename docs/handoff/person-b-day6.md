# Person B Day 6 Handoff

## Owned files

- `backend/app/services/commerce/**`
- `backend/app/services/wallet/**`
- Day 6 route-state helpers in `backend/app/services/trip/service.py` and `deterministic.py`
- `data/commerce/**`
- `tests/backend/unit/test_day6_commerce.py`
- `tests/backend/unit/test_day6_wallet.py`
- Day 6 additions in `tests/backend/unit/test_route_service.py`

## Day 6 requirements covered

- Simulated vignette purchases with current route and requirement validation.
- Deterministic Hungarian 10-day vignette price of 16.5 EUR.
- Simulated hotel-room and restaurant-table bookings with exact result-category checks.
- Guest, date, time, route, search, result, confirmation, and booking-type validation.
- Stable transaction IDs, booking IDs, confirmation codes, and idempotent request keys.
- Wallet states: READY, PROCESSING, COMPLETED, DECLINED, and DUPLICATE.
- Phone confirmation states: PENDING, SENT, and FAILED.
- Deterministic multi-stop charging selection ordered by route progress.
- Remaining distance, duration, ETA, next mandatory stop, and charging-status facts.
- Tests proving selection alone does not create a booking or transaction.

## Contract assumptions

- Route and search context are supplied by the owning route service.
- Vignette requirement `hu-vignette-10d` uses EUR and costs 16.5.
- Booking types are `hotel_room` and `restaurant_table`.
- HTTP/Realtime camelCase conversion remains owned by the shared contract/API owner.

## Timing/UX assumptions

- Wallet state is in memory and resets with a new service/browser session.
- Missing hotel dates use the current local date as the documented demo default.
- Restaurant bookings require an explicit `HH:MM` time.
- Route-state facts are compact Python mappings for the shared API layer to serialize.

## Tests run

- `\.venv\Scripts\python.exe -m pytest tests/backend/unit/test_day6_commerce.py tests/backend/unit/test_day6_wallet.py -q`
- `\.venv\Scripts\python.exe -m pytest tests/backend -q`
- `git diff --check`

## Manual checks still needed

- Exercise the shared API/Realtime tools after their owning integration is wired.
- Verify the frontend displays wallet, booking, phone-confirmation, and driving facts.

## Known limitations

- No live payment, hotel, restaurant, government, or notification provider is called.
- Commerce JSON files are local fixture/catalog inputs; runtime wallet state intentionally remains in memory for refresh reset behavior.
