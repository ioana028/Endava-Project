# Demo Scenarios

## Scenario A: Fastest route

Driver presses `Start Suzanne`, then says: `Take me to Budapest fast.`

Expected Realtime story:

- the local listening jingle plays immediately;
- Realtime calls `plan_route` with Budapest and `FASTEST`;
- the backend returns the full structured route to the frontend;
- the map displays the route and the summary displays distance and duration;
- only compact destination, distance, duration, and vehicle-alert facts return
  to Realtime for narration;
- the driver presses `Stop Suzanne` to close the session and release the
  microphone.

This scenario proves explicit Start -> Realtime voice -> deterministic tool ->
map update -> spoken result -> explicit Stop. Every route fact comes from the
backend; geometry never enters the model conversation.

## Scenario A2: Automatic safe route result and follow-up

While the same Realtime session is active:

```text
Driver: I want to get to Budapest as fast as possible, can you plot a route?
Suzanne: Aaalright, let me check.
Suzanne: Budapest is about 251 kilometres and roughly 3 hours 10 minutes including a charging stop at Ionity Győr. You cross into Hungary and need a Hungarian motorway vignette.
```

The exact duration, cost, road, charging requirement, vignette, and weather
facts must come from deterministic services or configured provider data. The
example wording is illustrative and must not be hard-coded with invented
facts.

## Scenario B: Family context

Driver: `Actually, we are travelling with the kids.`

The conversation retains Budapest and the active route priority while adding a
family-friendly preference. Future ranking can prefer food, toilets, rest, and
other suitable stops without losing the driver's fastest-route choice.

## Scenario C: Vehicle and weather

A deterministic weather input identifies snow along a route segment while the
vehicle fixture reports summer tyres. The system creates a vehicle/weather
alert. The LLM may explain the returned alert but may not create it.

## Scenario D: Border, vignette, and partner distinction

The route enters Hungary. Suzanne detects the Austria-Hungary border crossing
and reports the Hungarian motorway vignette as a route requirement. The
Hungarian vignette is listed in `partners.json` for future simulated commerce,
but it has no partner benefit. Partner or discount placement never overrides
route safety or driver intent.

## Scenario E: Generic food stop

Driver: `I want to stop to eat.`

Suzanne searches generic POI data along the active route and returns suitable
food stops ranked by detour and route relevance. A result is valid even when
there is no partner relationship or discount attached.

## Scenario E2: Generic hotel or attraction search

Driver: `Find a hotel near the route.`

Suzanne searches generic route-aware POI data and returns a factual hotel
result. The same flow supports restaurants, tourist attractions, coffee, rest,
and charging. Searching does not alter the active route unless the driver
explicitly asks Suzanne to add the place as a stop.

## Scenario F: Dining and commerce

Driver: `Pay the tolls and book a restaurant near my destination, I want Italian.`

Suzanne pays the mandatory toll through the simulated in-car wallet, then
searches for Italian restaurants near the destination. It may mention a
partner's 10% discount as optional enrichment:

```text
Suzanne: Toll paid using your in-car wallet.
Suzanne: I'm now looking for a restaurant. We have a partner five minutes from your destination with a 10% discount. Should I book that?
Driver: Yes, thank you.
Suzanne: Done, let's begin.
```

The approval and confirmation are voice-only. Booking and payment remain
simulated and must never be represented as real financial activity.