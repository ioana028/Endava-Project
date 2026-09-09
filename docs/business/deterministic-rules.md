# Deterministic Business Rules

## Non-negotiable boundary

The LLM can infer that the driver wants the fastest route. It cannot decide
which route is fastest, how much energy a journey consumes, or whether a stop
is required. Those decisions belong to deterministic code and provider data.

## Demo route facts

The demo corridor is Vienna, Austria to Budapest, Hungary, approximately
243 km via the M1 motorway. The fixture vehicle begins with an estimated range
of 95 km. Therefore a charging stop is required for the demonstration.

The initial fixture identifies Ionity Győr as the intended charging stop. A
future routing implementation must validate the stop against route position,
vehicle compatibility, energy need, and detour rather than selecting it only
because it has a partner label.

## Ranking order

Recommendations are evaluated in this order:

1. Safety and hard vehicle requirements.
2. Fuel/charging compatibility.
3. Explicit driver route priority.
4. Journey suitability and detour.
5. Family or other contextual preferences.
6. Partner/commercial preference as a secondary differentiator.

A sponsored location must not introduce a material detour when the driver
requested the fastest route.

## Generic POI rule

Food, coffee, rest, toilets, and other stop searches must work from generic
POI data. A partner relationship is optional enrichment, not a requirement
for a result. For an active route, rank candidates using:

1. Hard compatibility and availability constraints.
2. Position relative to the route or destination.
3. Detour time and journey impact.
4. Explicit driver preferences, such as Italian food.
5. Ratings or other quality signals.
6. Partner benefit as a secondary differentiator.

`I want to stop to eat` therefore produces a food POI search even if every
candidate is non-partner.

## Route narration rule

Suzanne may narrate a completed route only from returned facts. A route
summary can include destination, duration, main road, estimated cost,
mandatory charging, mandatory toll/vignette requirements, and route weather
alerts. Missing data must be omitted or described as unavailable; it must not
be guessed by the LLM.

## Energy and stops

At minimum, tests should cover:

- insufficient range causes a charging stop requirement;
- sufficient range does not create a fabricated stop;
- a stop incompatible with the vehicle is rejected;
- detour/time is included when comparing candidates;
- partner status cannot override compatibility or explicit priorities.

Exact consumption and charging formulas should live in named services and be
documented beside their tests when implemented.

## Alerts

Weather and vehicle warnings require both a deterministic weather/context
input and the relevant vehicle state. The assistant may phrase a returned
warning but may not invent either input.