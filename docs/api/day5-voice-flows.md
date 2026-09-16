# Day 5 Voice Flows

This document is the executable conversation contract for Day 5 realtime work.
Suzanne may interpret natural language, but every factual result comes from a
backend tool response. Suzanne must not calculate route position, radius,
detour, availability, opening hours, ratings, or partner benefits herself.

## Canonical search intents

| Driver intent | Tool intent | Scope | Route mutation |
|---|---|---|---|
| "What can I see along the route?" | route attraction search | Route corridor, excluding the first and last 10 km by default | No |
| "Find an attraction near Budapest." | destination attraction search | Destination-centered provider search | No |
| "What is near the charging station?" | charging-stop amenity search | 500 m around the selected charging stop | No |
| "Find coffee and food around that charger." | charging-stop amenity search | 500 m around the selected charging stop | No |
| "Take me through that restaurant." | explicit reroute request | Selected POI plus current route context | Only after confirmation |

A search near a charging stop is not a request to add a waypoint. Selecting,
naming, or displaying a result is not reroute confirmation.

## Route attraction flow

Driver:

> What can I see along the route?

Suzanne calls the route-scoped attraction search with the current active route
and the attraction category. The deterministic service applies the configured
route corridor, excludes the first and last 10 km, ranks the results, and
returns factual `StopPinpoint` values.

Suzanne:

> I found two attractions along the route. The first is the Old Town viewpoint,
> with an estimated 8 minute detour. The second is the riverside museum, with a
> 12 minute detour. Would you like details about either one?

The response may mention only fields returned by the backend. A partner offer
may be mentioned only when it is attached to that returned provider result.

## Destination attraction flow

Driver:

> Find a tourist attraction near Budapest.

Suzanne uses destination scope because the driver explicitly named the
destination. The result must not be described as being along the route unless
the backend returned it from the route-scoped search.

Suzanne:

> I found the Budapest History Museum near your destination. It is an
> attraction with an estimated 15 minute detour from the destination area.

If no result is returned:

> I could not find a matching attraction near Budapest. I can search along the
> route instead if you would like.

## Charging-stop amenity flow

Precondition: a current route contains a selected charging stop. The frontend
must preserve the selected stop reference and the current route context.

Driver:

> Are there any amenities near that charging station?

or:

> Find coffee and food around the charging stop.

Suzanne calls `search_stop_amenities` with the selected charging-stop
reference, requested categories, and the current route context. The backend
searches a deterministic 500 m radius around that stop. The tool is read-only:
it must not add a waypoint, replace the route, or select a result for rerouting.

The canonical request keeps the context identifiers separate:

```json
{
  "stopId": "place-chargepoint-parndorf",
  "routeId": "active-route-id",
  "searchId": "active-search-id",
  "categories": ["food", "coffee", "rest", "shopping"]
}
```

The compact tool result contains only the selected stop name, bounded result
facts, and the fixed search radius. Coordinates, geometry, and raw provider
payloads stay in frontend state and never enter Realtime messages:

```json
{
  "status": "success",
  "selectedStopName": "ChargePoint Parndorf",
  "radiusMeters": 500,
  "results": [
    {
      "id": "place-456",
      "name": "Parndorf Shopping Complex",
      "category": "shopping",
      "amenities": ["food", "coffee"],
      "distanceMeters": 350
    }
  ]
}
```

Suzanne:

> Yes. ChargePoint Parndorf is near a shopping complex with food and coffee.

The compact response contains only:

- selected charging-stop name;
- result name and category;
- factual amenities returned by the provider;
- factual distance or radius information;
- optional provider brand and partner enrichment when present.

Do not claim that a location is open, available, rated, or a partner location
unless that exact fact was returned by the backend.

If there is no selected charging stop:

> I do not have a selected charging stop yet. I can plan the route first, then
> search for amenities around its charging stop.

If the stop is stale or no longer belongs to the active route:

> That charging stop is no longer part of the active route. I cannot search
> around it until the route is refreshed.

## Explicit reroute flow

Driver:

> Take me through the riverside museum.

Suzanne must not reroute immediately. She first identifies the selected POI and
summarizes the proposed consequence using returned facts.

Suzanne:

> The riverside museum would add about 12 minutes to the route. Should I add it
> as a stop?

Driver:

> Yes, confirm it.

Only after the explicit confirmation does Suzanne call
`reroute-through-poi`. The request preserves both opaque identifiers from the
search response:

```json
{
  "poiId": "place-123",
  "routeId": "route-123",
  "searchId": "search-456",
  "confirmation": "confirmed"
}
```

The backend returns a complete replacement route. Suzanne may say that the
route changed only after that call succeeds. On failure, she reports the
returned error without claiming a route change.

## State and error behavior

The frontend and realtime bridge must expose these states distinctly:

- `loading`: the search or tool call is in progress;
- `success`: factual results are available;
- `empty`: the call succeeded but returned no results;
- `stale`: the route, selected stop, or search context is no longer current;
- `failure`: the call failed and includes the backend error code/message.

The frontend maps backend `route_id` and `search_id` to frontend `routeId` and
`searchId`. It preserves both values unchanged for rerouting. It must not
combine the two identifiers into another context value.

## Test examples

Person C's backend and realtime tests should cover:

1. route attraction language selects route scope;
2. an explicit destination selects destination scope;
3. "near that charger" selects the charging-stop scope;
4. charging-stop search uses 500 m and does not mutate the route;
5. no selected stop returns a clear precondition error;
6. stale route, stop, and search contexts are rejected;
7. rerouting requires explicit confirmation and both context identifiers;
8. empty and provider failure results remain distinguishable;
9. compact results contain no geometry, raw provider payload, or invented fact.

Person A owns browser and hook tests under `tests/frontend/**`. Person C must
provide the expected events and payloads for those tests and review the
coverage without editing A-owned files.
