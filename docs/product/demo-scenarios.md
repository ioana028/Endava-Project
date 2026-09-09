# Demo Scenarios

## Scenario A: Fastest route

Driver: `Suzanne, take me to Budapest fast.`

Expected Day 1 story:

- microphone capture and Whisper transcript;
- intent contains destination Budapest and `FASTEST` priority;
- backend returns the extracted intent to the frontend;
- Suzanne speaks exactly: `Calculating route based on your preferences, hold on`;
- no route is calculated or shown yet;
- no confirmation button is rendered.

Day 1 proves voice input -> AI intent -> backend response -> voice output.
Route geometry, route statistics, and charging logic are Day 2 work.

## Scenario A2: Smart route result and follow-up

After routing is implemented, the same interaction continues:

```text
Driver: Hey Suzanne
Suzanne: Yeah?
Driver: I want to get to Budapest as fast as possible, can you plot a route for me?
Suzanne: On it, give me a second.
Suzanne: Your route is being displayed. You can get to Budapest in 2 hours 45 minutes via the M1. Total trip cost is estimated at 42 euros with a mandatory charging stop at Ionity Győr and a mandatory Hungarian vignette. Heavy rain is expected near Győr. Would you like any more help?
```

The exact duration, cost, road, charging requirement, vignette, and weather
alert must come from deterministic services or configured provider data. The
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

## Scenario D: Partner and vignette

The route enters Hungary. Suzanne may eventually offer a simulated e-vignette
purchase and requires explicit spoken confirmation. There are no on-screen
confirmation buttons. Partner or discount placement never overrides route
safety or driver intent.

## Scenario E: Generic food stop

Driver: `I want to stop to eat.`

Suzanne searches generic POI data along the active route and returns suitable
food stops ranked by detour and route relevance. A result is valid even when
there is no partner relationship or discount attached.

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