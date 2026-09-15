# Post-Day 4 Roadmap

## Purpose

Day 4 completes the core route intelligence loop:

```text
Driver speaks -> Suzanne understands -> deterministic services calculate
-> provider data enriches -> map updates -> driver confirms consequential changes
```

This document records the next product and presentation opportunities so they are
not lost after Day 4. The priorities below should preserve the existing
architecture:

- deterministic services calculate route, vehicle, weather, commerce, and POI facts;
- Suzanne interprets and narrates returned facts;
- provider adapters own external API details;
- the frontend owns geometry, map state, and rich visual presentation;
- consequential actions require explicit driver confirmation;
- simulated payments and bookings must never be represented as real transactions.

## Priority order

### Phase 1: Product completion

1. Simulated commerce flows.
2. Persistent trip and conversation context.
3. Route alternatives and explicit route comparison.
4. Journey briefing and route intelligence timeline.
5. Arrival summary.

### Phase 2: Presentation intelligence

1. What-if route simulation.
2. BEV energy forecast.
3. Weather impact layer.
4. Source and confidence indicators.
5. Journey modes and preference-aware planning.

### Phase 3: Reliability and polish

1. End-to-end demo scenarios.
2. Provider degradation and recovery.
3. Accessibility and interaction polish.
4. Observability and diagnostics.
5. Performance and security review.

## 1. Simulated commerce flows

Complete the product story of `understand -> plan -> adapt -> recommend -> book/pay`.

### Vignette purchase

Suzanne should be able to explain that a vignette is required, offer a
simulated purchase, ask for voice confirmation, and return a clear result.

The flow must distinguish:

- route requirement: the vehicle needs a vignette for the planned route;
- commerce action: the driver has asked Suzanne to simulate purchasing it;
- partner enrichment: a partner may offer a benefit, but the requirement does
  not depend on partner status.

### Toll payment

Add a simulated in-car wallet flow for mandatory toll sections:

1. summarize the toll requirement and simulated cost when available;
2. ask for explicit confirmation;
3. execute the deterministic simulated payment tool;
4. return a payment receipt/status fact;
5. never claim that a real payment occurred.

### Restaurant or hotel booking

Support a voice-only simulated booking flow after a POI search:

1. search provider-backed results;
2. select a result;
3. present factual name, location, rating, amenities, and estimated detour;
4. ask for confirmation;
5. return a simulated booking confirmation.

The booking flow must work for non-partner POIs. Partner discounts are optional
enrichment, not a prerequisite for a useful result.

## 2. Persistent trip and conversation context

Keep useful context across follow-up requests and Realtime session restarts.

The assistant should understand requests such as:

- `Find somewhere to eat after the charging stop.`
- `Make that stop shorter.`
- `Actually, avoid tolls.`
- `We are travelling with two children.`
- `Use the scenic route instead.`

Context should include only validated structured facts, such as:

- active destination;
- active route and route identifier;
- route priority;
- selected POI or waypoint;
- charging requirements;
- driver preferences;
- family/accessibility preferences;
- pending confirmation state.

Do not rely on an unbounded transcript as the source of truth. Backend services
must validate references against the current active route/session.

## 3. Route alternatives and comparison

Allow Suzanne to compare fastest, cheapest, scenic, balanced, and EV-oriented
alternatives without immediately replacing the active route.

A comparison should show:

- total distance and duration;
- charging stops and charging time;
- toll and estimated route cost;
- borders and vignette requirements;
- weather alerts;
- major detour or road differences;
- why Suzanne recommends one option.

Example explanation:

```text
The fastest route is 12 minutes quicker, but the balanced route avoids tolls
and has a shorter charging stop.
```

The active route changes only after explicit selection and confirmation.

## 4. Journey briefing and route intelligence timeline

### Journey briefing

After route calculation, Suzanne should provide a compact, polished briefing:

> This route is approximately 251 kilometres and takes about 3 hours. You need
> one charging stop, cross into Hungary, and require a Hungarian motorway
> vignette. Rain is expected near the middle of the journey.

Every statement must be backed by returned deterministic facts.

### Route intelligence timeline

Show the journey as a chronological timeline containing events such as:

- origin;
- border crossing;
- charging stop;
- optional selected POI;
- toll section;
- weather segment;
- destination.

Each event can show distance, estimated arrival time, reason, and whether it is
mandatory or optional. The timeline makes backend intelligence visible during a
presentation without exposing raw provider payloads.

## 5. What-if route simulation

Add temporary route proposals that do not mutate the active route:

- `What if we avoid tolls?`
- `What if we stop for lunch?`
- `What if we leave with 20 percent less battery?`
- `What if we take the scenic route?`

Show the proposed difference in:

- duration;
- distance;
- charging requirements;
- toll cost;
- vignette/border requirements;
- weather exposure;
- total estimated trip cost.

The proposal remains visibly separate from the active route until the driver
confirms it.

## 6. BEV energy forecast

Make the vehicle intelligence visible with an energy graph across the route.

The graph should display:

- projected battery percentage at route milestones;
- current range and safety reserve;
- weather-adjusted consumption when supported;
- charging stop location and expected charging duration;
- the consequence of removing or adding a charging stop;
- comparison between active and proposed routes.

Example conceptual display:

```text
Battery
100% |\\
 75% | \\\        /\\
 50% |  \\______/    Charging stop
 25% |
  0% +----------------------------
       Origin       Stop    Destination
```

The frontend renders the graph. The backend remains responsible for the
calculation and safety decision.

## 7. Weather impact layer

Place route weather conditions directly on the map and timeline:

- rain zone;
- snow zone;
- strong wind zone;
- slippery-road warning;
- vehicle-specific tyre warning.

Keep the reasoning explicit:

- the weather provider reports snow;
- deterministic vehicle policy decides whether the vehicle state creates an
  alert;
- Suzanne narrates only the resulting structured alert.

## 8. Source and confidence indicators

Expose factual provenance in a compact, understandable way:

- `Vehicle telemetry`;
- `Google Routes`;
- `Google Places`;
- `Weather provider`;
- `Partner enrichment`;
- `Estimated`.

Use these indicators for important route, weather, POI, and commerce facts. Do
not expose API internals, raw JSON, or credentials.

This is especially useful during a technical presentation because it shows
which information was calculated, fetched, estimated, or optionally enriched.

## 9. Journey modes and driver preferences

Add explicit modes that change deterministic ranking and planning policy:

- Fastest;
- Cheapest;
- Scenic;
- Balanced;
- EV range;
- Weather cautious;
- Family.

Family mode may prioritize toilets, rest areas, food, and shorter driving
segments when provider data supports those claims. EV range mode may prefer
charging availability and reserve margin. Modes must affect structured policy,
not only Suzanne's wording.

## 10. Accessible and discoverable consequential actions

Keep the product voice-first while making the demonstration easy to follow.

The interface may expose actions such as:

- select stop;
- ask Suzanne to add stop;
- compare route;
- pay vignette;
- pay toll;
- book restaurant;
- apply alternative.

Selection should never silently perform a consequential action. The UI can
prepare intent or confirmation state, while Suzanne or an explicit confirmation
step completes the operation according to the agreed product rules.

## 11. Arrival experience

Give the journey a clear final state rather than ending when the route first
appears.

The arrival summary may include:

- total distance and driving time;
- charging stops and charging time;
- toll and vignette status;
- selected POIs or completed simulated bookings;
- estimated trip cost;
- relevant weather or vehicle alerts;
- a concise trip recap.

## 12. Reliability, security, and observability

### Reliability

Add and demonstrate:

- provider timeouts and bounded retries;
- cancellation of obsolete requests;
- stale route and POI protection;
- graceful degradation when Places, weather, or routing is unavailable;
- recovery after a Realtime connection interruption;
- deterministic offline/demo mode for presentations.

### Observability

Record safe diagnostics such as:

- route/tool operation name;
- provider category;
- request count;
- latency;
- result count;
- failure code;
- active session correlation ID.

Never log API keys, authorization headers, raw provider payloads, or sensitive
conversation content.

### Security review

Verify:

- browser code contains no server provider keys;
- tool inputs are validated at the backend boundary;
- POI and route identifiers cannot be mixed across sessions;
- arbitrary coordinates cannot force a reroute;
- simulated commerce cannot be mistaken for real payment or booking;
- user-facing errors reveal no stack traces or provider internals.

## 13. Testing and demo reliability

Create deterministic automated scenarios for:

- voice request to route display;
- automatic charging;
- border, toll, and vignette detection;
- route-wide POI discovery;
- explicit POI rerouting;
- route comparison;
- what-if simulation;
- simulated toll/vignette payment;
- simulated booking;
- provider failure and recovery;
- Stop and Realtime restart;
- arrival summary.

Automated tests must use mocked providers. Live Google/OpenAI calls remain local
manual acceptance checks only.

Add a pre-demo health check covering:

- backend availability;
- frontend availability;
- map configuration;
- server provider configuration;
- microphone permission;
- Realtime connectivity;
- provider latency and quota status.

## Suggested presentation sequence

A strong final demonstration can follow this order:

1. Start Suzanne and ask for the fastest route.
2. Show the route briefing, charging decision, border, vignette, toll, and
   weather facts.
3. Show the energy forecast and journey timeline.
4. Ask for coffee or food along the route.
5. Select a POI and show that the route does not change yet.
6. Ask Suzanne to add it and confirm the reroute.
7. Compare the new route with a toll-free or scenic alternative.
8. Demonstrate a what-if battery or weather scenario.
9. Simulate vignette/toll payment or restaurant booking.
10. Stop and restart Suzanne while preserving the route state.
11. Finish with the arrival summary.

## Definition of success

The post-Day 4 work is successful when Suzanne feels like a trustworthy,
vehicle-aware journey assistant rather than a voice interface placed on top of
a map. The strongest evidence is that the system can explain its decisions,
compare alternatives, adapt to vehicle and weather conditions, obtain useful
provider-backed recommendations, and require the driver's approval before any
meaningful route or commerce action changes state.
