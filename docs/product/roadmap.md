# Delivery Roadmap

## Day 0: shared foundation

- Agree on these docs and `contracts.ts`.
- Confirm ownership and branch workflow.
- Copy `.env.example` to local `.env` without committing it.
- Decide the smallest fake-provider path for tests.

## Day 1: walking skeleton

Deliver the voice input -> AI intent -> backend intent response -> voice
output path described in [Day 1 Walking Skeleton](day1-walking-skeleton.md).
Do not add route calculation or on-screen confirmation buttons.

## Day 2 and after: smart route planning

Day 2 turns the Day 1 intent into a real in-car smart route planner. The
planner is useful even when no partner is involved. A driver can ask for a
destination and a route style such as fastest, scenic, cheapest, or balanced;
the system returns a factual route and explains the required and optional
stops along it.

### 1. Route calculation

- Add geocoding and routing adapters.
- Resolve the origin from the configured vehicle position and the destination
	from the assistant intent.
- Support `FASTEST`, `SCENIC`, `CHEAPEST`, and `BALANCED` route priorities.
- Return route geometry, distance, duration, main road, and estimated cost.
- Render the route on the map and keep all route facts in `RouteResponse`.

### 2. Mandatory journey stops

- Compare route distance and energy demand with the vehicle's current range.
- Identify mandatory charging stops for a BEV when the destination or the next
	viable segment cannot be reached safely.
- Identify mandatory tolls, vignettes, border requirements, and other route
	constraints from route and country data.
- Include mandatory stops and requirements in the structured route result.
- Never present a partner location as mandatory merely because it is a
	commercial partner.

### 3. Weather and route context

- Query weather for relevant route segments and stop areas.
- Produce deterministic `RouteAlert` values for heavy rain, snow, ice,
	dangerous wind, or other relevant conditions.
- Combine weather facts with vehicle state, such as tyre type, before creating
	a vehicle-related warning.
- Have Suzanne speak concise alerts without inventing weather details.

### 4. Generic POI discovery

POI discovery is a general route capability, not a partner lookup. The driver
must be able to say:

```text
I want to stop to eat.
Find coffee near the route.
We need a rest stop with toilets.
Find an Italian restaurant near my destination.
```

Implement:

- POI search along the route, near a selected stop, or near the destination.
- Categories for food, coffee, rest, toilets, charging, and service needs.
- Ranking by route relevance, detour, availability when known, driver
	preferences, and suitability.
- `StopPinpoint` results that can exist without a partner offer.
- Partner offers as optional enrichment on a relevant POI, never as a
	prerequisite for returning useful results.

### 5. Conversational follow-ups

After displaying a route, Suzanne should offer useful next steps through
voice, for example:

```text
Your route is being displayed. You can reach Budapest in 2 hours 45 minutes
via the M1. The trip requires a charging stop at Ionity Győr and a Hungarian
vignette. Heavy rain is expected near Győr. Would you like any more help?
```

Follow-ups should preserve the active trip and understand requests such as:

- `I want to stop to eat` as a generic POI search;
- `Book an Italian restaurant near my destination` as POI search followed by
	optional booking;
- `Pay the tolls` as a commerce request for a mandatory route requirement.

The assistant orchestrates these requests, but deterministic services return
the route, POI, weather, toll, price, and booking facts.

## Final presentation polish

- Add generic route and POI cards alongside optional partner enrichment.
- Add voice-only simulated toll payment and restaurant booking flows.
- Add conversation follow-ups and reranking without losing the active route.
- Add animation and the optional 3D cockpit only after core route behavior
	works.

Every item should be tied to a demo scenario and should not weaken local
reliability or the deterministic/LLM boundary.