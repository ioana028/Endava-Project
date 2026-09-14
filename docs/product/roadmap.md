# Delivery Roadmap

## Day 0: shared foundation

- Agree on these docs and `contracts.ts`.
- Confirm ownership and branch workflow.
- Copy `.env.example` to local `.env` without committing it.
- Decide the smallest fake-provider path for tests.

## Day 1: walking skeleton (historical)

The original walking skeleton documented the upload/intent/TTS path. It remains
historical compatibility context; the active voice architecture is the
Start/Stop Realtime WebRTC session described below.

## Day 2 and after: smart route planning on Realtime

Day 2 turns the route request into a real in-car smart route planner. The
driver starts one Realtime session and can ask for a route and follow-up
actions without another wake word or recording upload. The planner is useful
even when no partner is involved. A driver can ask for a
destination and a route style such as fastest, scenic, cheapest, or balanced;
the system returns a factual route and explains the required and optional
stops along it.

### 1. Route calculation

- Add geocoding and routing adapters.
- Resolve the origin from the configured vehicle position and the destination
	from the assistant intent.
- Support `FASTEST`, `SCENIC`, `CHEAPEST`, and `BALANCED` route priorities.
- Return route geometry, distance, duration, main road, and estimated cost to
	the frontend. Send only compact narration facts back to Realtime.
- Render the route on the map and keep all route facts in `RouteResponse`.

### 2. Mandatory journey stops and route requirements

- Compare route distance and energy demand with the vehicle's current range.
- Automatically identify and add mandatory charging stops for a BEV when the
	destination or the next viable segment cannot be reached safely.
- Identify mandatory tolls, vignettes, border requirements, and other route
	constraints from route and country data.
- Include mandatory stops and requirements in the structured route result and
	narrate final total duration, including charging time when applicable.
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
- Categories for charging, hotels, restaurants, tourist attractions, food,
	coffee, rest, toilets, and service needs.
- Ranking by route relevance, detour, availability when known, driver
	preferences, and suitability.
- `StopPinpoint` results that can exist without a partner offer.
- Partner offers as optional enrichment on a relevant POI, never as a
	prerequisite for returning useful results.

### 5. Realtime conversational follow-ups

After automatically completing a route, Suzanne should report final facts and
remain ready for useful voice follow-ups, for example:

```text
Your route to Budapest is roughly 3 hours 10 minutes including a charging stop
at Ionity Győr. You cross from Austria into Hungary and need a Hungarian
motorway vignette. Would you like a hotel, restaurant, or attraction near the
route?
```

Follow-ups stay inside the active Realtime session and should understand
requests such as:

- `I want to stop to eat` as a generic POI search;
- `Find a hotel near the route` as a generic POI search;
- `Find a tourist attraction near my destination` as a generic POI search;
- `Book an Italian restaurant near my destination` as POI search followed by
	optional booking;
- `Pay the tolls` as a commerce request for a mandatory route requirement.

The assistant orchestrates these requests, but deterministic services return
the route, POI, weather, toll, price, and booking facts.

Each capability must have a focused backend tool and compact result schema.
Never place full geometry, provider payloads, or unrelated trip data in the
Realtime conversation.

## Final presentation polish

- Add generic route and POI cards alongside optional partner enrichment.
- Add voice-only simulated toll payment and restaurant booking flows.
- Add conversation follow-ups and reranking without losing the active route.
- Add animation and the optional 3D cockpit only after core route behavior
	works.

Every item should be tied to a demo scenario and should not weaken local
reliability or the deterministic/LLM boundary.