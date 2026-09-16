# API Contracts

## Status and authority

This documents the active Realtime session/tool APIs. The TypeScript
definitions in `frontend/src/types/contracts.ts`
remain the canonical names and shapes for frontend-facing route data.

## Local runtime

| Service | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| Health | `GET http://localhost:8000/health` |

The frontend uses `VITE_API_BASE_URL` when present and otherwise targets the
local backend URL. The backend reads configuration from the root `.env`.

## Protocol conventions

- JSON property names are camelCase.
- JSON endpoints use `Content-Type: application/json`.
- The active voice path uses a browser WebRTC Realtime session.
- Coordinates in route geometry and stop tuples are `[longitude, latitude]`.
- Distances are kilometres, durations are minutes, and prices are EUR.
- API keys and provider prompts never cross the backend/frontend boundary.
- The frontend consumes structured response fields; it must not parse speech to
  decide whether to draw a route or show a stop.
- The frontend receives the full structured route for rendering, but sends only
  compact narration facts back to Realtime. It must never send route geometry
  or map-only data to the model.
- The LLM may extract intent, but deterministic services own route, vehicle,
  station, price, weather, and transaction facts.
- Confirmations are voice-only. There are no on-screen confirmation buttons.

## `GET /health`

### Response `200`

```json
{
  "status": "ok",
  "service": "backend",
  "environment": "development"
}
```

`environment` comes from `ENVIRONMENT`. Health must not require OpenAI or
Google Maps Platform to be available.

### `GET /health/config`

Returns non-secret provider configuration state for local diagnostics. The
response includes boolean `openaiConfigured`, `googleRoutesConfigured`, and
`googlePlacesConfigured` fields plus the resolved `placesProvider` value
(`google` or `offline`). Credentials and provider payloads are never returned.

## `POST /api/assistant/realtime/session`

Creates a short-lived browser credential. The server API key, instructions, and
tool schemas never cross this boundary.

```json
{
  "clientSecret": "ek_...",
  "model": "gpt-realtime-2.1-mini"
}
```

The browser uses the returned model when posting its SDP offer to OpenAI.

## Realtime POI voice flow

`search_route_poi` is read-only. Suzanne maps driver language to the
provider-neutral categories `attraction`, `restaurant`, `hotel`, `charging`,
`coffee`, `rest`, `toilets`, `fuel`, and `service`. A search returns suggestions
only and must not change the active route.

`search_stop_amenities` is a separate read-only operation for a selected
charging stop. Its request preserves the current context identifiers separately:

```json
{
  "stopId": "place-chargepoint-parndorf",
  "routeId": "active-route-id",
  "searchId": "active-search-id",
  "categories": ["food", "coffee", "rest", "shopping"]
}
```

The compact result includes the selected stop name, up to four provider-backed
amenity results, factual distance fields when returned, and the fixed
`radiusMeters: 500` fact. It contains no coordinates, geometry, or raw provider
payload. The operation never adds a waypoint or changes the route.

The browser forwards the full structured POI response to the map, but sends
only compact facts to Realtime:

```json
{
  "status": "success",
  "results": [
    {
      "id": "place-123",
      "name": "Example Cafe",
      "category": "coffee",
      "rating": 4.5,
      "tag": "Cafe",
      "detourMinutes": 6
    }
  ]
}
```

Coordinates, geometry, raw provider fields, and map-only data are never sent
to Realtime. Suzanne must describe only returned facts. A fuel result alone
does not establish that coffee, toilets, or rest facilities are available.

## `POST /api/assistant/realtime/tools/reroute-through-poi`

Rerouting is a separate mutation from search and is called only after the
driver explicitly accepts Suzanne's proposed route change. Selecting, naming,
or tapping a POI is not confirmation.

```json
{
  "poiId": "place-123",
  "routeId": "route-123",
  "searchId": "search-456",
  "confirmation": "confirmed"
}
```

`routeId` and `searchId` are separate opaque identifiers created by the backend
POI search. The browser must preserve both values exactly and send both back
for rerouting; Suzanne must never invent, rename, combine, or substitute
either value. The backend uses `route_id` and `search_id`; the frontend uses
`routeId` and `searchId`.

`routeId` identifies the active route snapshot. `searchId` identifies the POI
search that produced the selected result. A reroute is valid only when both
identifiers still match the current route and search state.
The successful response contains a complete replacement `RouteResponse`; the
browser returns only compact distance, duration, charging, and relevant route
requirement facts to Realtime. Suzanne cannot claim that the route changed
until this tool succeeds.

Tool failures use the common error envelope. The browser preserves `code` and
`message` when returning an error to Realtime, including `REROUTE_UNAVAILABLE`,
`STALE_POI_SELECTION`, and `POI_UNAVAILABLE`.

## `POST /api/assistant/realtime/tools/plan-route`

The browser forwards only the Realtime function arguments to the deterministic
route service:

```json
{
  "destination": "Budapest",
  "priority": "FASTEST"
}
```

The response contains the full `RouteResponse` for the map. The browser then
sends only this compact result back to Realtime:

```json
{
  "status": "success",
  "destination": "Budapest",
  "distanceKm": 243,
  "drivingDurationMinutes": 165,
  "totalDurationMinutes": 190,
  "chargingStop": "Ionity Győr",
  "borderCrossings": ["Austria-Hungary"],
  "routeRequirements": ["Hungarian motorway vignette"]
}
```

`geometry`, `stops`, prices, and map presentation fields remain frontend data;
they are not narration input.

## Canonical response types

These definitions mirror `frontend/src/types/contracts.ts`.

```ts
type RoutePriority = 'FASTEST' | 'CHEAPEST' | 'SCENIC' | 'BALANCED';

type StopCategory =
  | 'charging'
  | 'food'
  | 'rest'
  | 'toll'
  | 'vignette'
  | 'service';

interface VehicleState {
  vehicleId: string;
  propulsion: 'BEV';
  batteryPercent: number;
  estimatedRangeKm: number;
  consumptionRateKwh: number;
  tyres: 'SUMMER' | 'WINTER' | 'ALL_SEASON';
  odometerKm: number;
}

interface Coordinates {
  lng: number;
  lat: number;
}

interface StopPinpoint {
  id: string;
  name: string;
  category: StopCategory;
  coords: [number, number];
  rating?: number;
  tag: string;
  detourMinutes: number;
}

interface RouteAlert {
  type: 'WEATHER' | 'TRAFFIC' | 'TOLL' | 'VEHICLE';
  locationName?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
}

interface TripStats {
  totalDistanceKm: number;
  totalDurationMinutes: number;
  totalPriceEur: number;
}

interface RouteResponse {
  origin: string;
  destination: string;
  stats: TripStats;
  geometry: [number, number][];
  stops: StopPinpoint[];
  alerts: RouteAlert[];
}

interface AssistantIntent {
  destination: string;
  priority: RoutePriority;
}

interface AssistantResponse {
  transcript: string;
  intent: AssistantIntent;
  spokenResponse: string;
  audioBase64?: string;
  route?: RouteResponse;
  toastMessage?: string;
}
```

## Post-Day-1 route extensions

The current `RouteResponse` is the minimum route shape already represented in
`frontend/src/types/contracts.ts`. The smart route planner will need additional
structured facts for route narration and follow-ups, including:

- the primary/main road used by the route;
- explicit mandatory charging requirements;
- explicit mandatory toll or vignette requirements;
- border crossings and driving versus total journey duration;
- optional generic POI results near the route or destination;
- route-segment weather context.

These should be added deliberately as shared contract changes. Until then:

- geometry and `origin`/`destination` describe the route;
- `TripStats` describes distance, duration, and estimated cost;
- `StopPinpoint` can represent charging, food, rest, toll, vignette, and
  service stops;
- `RouteAlert` carries weather and vehicle warnings;
- a partner offer must remain optional enrichment and must not be inferred from
  a `StopPinpoint`.

Do not put generic POI search behind the partner fixture. Requests such as
`I want to stop to eat`, `Find a hotel near the route`, and `Find a tourist
attraction near my destination` must be able to return non-partner
`StopPinpoint` results. The Hungarian vignette may be present in the partner
fixture, but its absence of a benefit must be preserved in the contract.

## Day 1 intent handoff

The AI module should produce a small internal typed intent, not a route:

```json
{
  "destination": "Budapest",
  "priority": "FASTEST"
}
```

This object is returned in `AssistantResponse.intent` on Day 1. It is the only
AI interpretation the frontend needs to receive at this stage. It is not a
route and must not be rendered as a route confirmation.

## Errors

Use a stable envelope:

```json
{
  "error": {
    "code": "INVALID_AUDIO",
    "message": "The uploaded audio format is not supported.",
    "requestId": "optional-request-id"
  }
}
```

Recommended statuses:

| Status | Code | Meaning |
|---:|---|---|
| 400 | `INVALID_REQUEST` | Invalid JSON or missing required input |
| 400 | `INVALID_AUDIO` | Empty, malformed, or unsupported recording |
| 413 | `PAYLOAD_TOO_LARGE` | Audio exceeds configured limit |
| 422 | `VALIDATION_ERROR` | Pydantic validation failure |
| 503 | `AI_UNAVAILABLE` | OpenAI or another required provider unavailable |
| 503 | `REROUTE_UNAVAILABLE` | Confirmed POI rerouting is unavailable |
| 409 | `STALE_POI_SELECTION` | The selected POI belongs to an old route/search context |
| 503 | `POI_UNAVAILABLE` | POI search is unavailable |
| 500 | `INTERNAL_ERROR` | Unexpected backend failure |

Do not expose API keys, stack traces, prompts, or raw provider errors.

## Compatibility rule

Changing a shared field, enum, coordinate convention, or endpoint requires a
small team discussion, an update here and in `contracts.ts`, and a check of
the frontend, backend, and integration tests before merging.