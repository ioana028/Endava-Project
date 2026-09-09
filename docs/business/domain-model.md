# Domain Model

## Driver and vehicle

`VehicleState` is the current demo vehicle condition:

- `vehicleId`: stable vehicle identifier;
- `propulsion`: currently only `BEV` is supported;
- `batteryPercent`: current charge from 0 to 100;
- `estimatedRangeKm`: deterministic current range estimate;
- `consumptionRateKwh`: kWh per 100 km;
- `tyres`: `SUMMER`, `WINTER`, or `ALL_SEASON`;
- `odometerKm`: current odometer.

The source fixture is `data/vehicles/telemetry.json`.

## Trip

The user expresses a destination and route preference. The initial priority
vocabulary is `FASTEST`, `CHEAPEST`, `SCENIC`, and `BALANCED`.

`RouteResponse` is the deterministic result and contains origin, destination,
trip statistics, route geometry, stops, and alerts. It represents the driver's
requested route plus factual mandatory requirements and useful optional stops.
A route is not merely a spoken answer: the map and cards consume its
structured fields.

## Stops and partners

`StopPinpoint` is a journey stop rendered by the route experience. Its
`category` is one of `charging`, `food`, `rest`, `toll`, `vignette`, or
`service`. A stop may come from a generic POI provider, deterministic vehicle
logic, route requirements, or a partner source. A partner offer may be
attached to a stop, but a commercial partner does not become a route fact
merely because it is sponsored.

The planner distinguishes:

- **Mandatory stops/requirements:** required by vehicle range, route country,
	toll, vignette, safety, or another hard constraint.
- **Optional stops:** useful suggestions such as food, coffee, rest, or a
	destination restaurant selected from generic POI data.
- **Partner enrichment:** a discount, booking option, or service attached to
	an otherwise relevant stop.

Current partner fixture entries are Ionity Győr, a Hungarian 10-day e-vignette,
and Trattoria Venice Budapest.

## Alerts

Alerts are deterministic contextual facts. Their types are `WEATHER`,
`TRAFFIC`, `TOLL`, and `VEHICLE`; severities are `INFO`, `WARNING`, and
`CRITICAL`. The message is concise enough for a driver-facing UI.

## Commerce vocabulary

Commerce is simulated for the prototype. A future implementation may model a
partner offer, booking, transaction, and vehicle wallet, but must not store raw
card credentials or claim a real financial transaction occurred. Any future
approval interaction is voice-only; the prototype does not use confirmation
buttons.