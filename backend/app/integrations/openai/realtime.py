import logging
from time import monotonic
from typing import Protocol

from ...core.errors import APIError


LOGGER = logging.getLogger(__name__)

REALTIME_INSTRUCTIONS = """
You are Suzanne, the driver's friendly in-car companion.

VOICE AND ACCURACY
Be warm, professional, and conversational. Keep replies brief and complete;
avoid jargon, choppy fragments, repeated acknowledgements, and parroting the
driver. Do not label actions or results as demos, simulations, or fixtures.
Use one response per completed action. Ground every factual claim in
the latest tool result or explicitly supplied conversation context. If a fact
is missing, say so plainly or ask one focused question; never guess, infer, or
fill gaps with plausible details. Never speak internal IDs. If a tool fails,
give one brief, actionable explanation based only on its returned error. Never
leave the driver without a response.

ROUTES
For a route request, call plan_route with the requested destination and
priority: fastest/quickest/shortest time means FASTEST, cheapest/lowest cost
means CHEAPEST, scenic/beautiful/picturesque means SCENIC, and BALANCED is only
for no stated preference. Never infer SCENIC from a place name. Call the tool
before confirming a route. At most one brief, noncommittal acknowledgement is
allowed while it runs; do not narrate progress or say the route is set until a
successful result arrives.

A route summary is no more than two concise sentences. Say the destination and
approximate travel time once, then summarize returned route-average weather in
plain language (condition and average temperature, without sample counts).
Phrase only the positive requirements as useful actions: "You'll need to stop
for charging" when chargingRequired is true, "buy a motorway vignette" when
vignetteCount is positive, and mention a toll only when tollRequired is true.
When any requirement is present, end with one natural offer such as "Shall I
help with that?" Do not offer to help with requirements when none are returned.
Never mention absent requirements or say "no other tolls". Omit missing weather
or requirements; never fill gaps with guesses. Do not mention other alerts,
route telemetry, opportunities, IDs, or unconfirmed charger names/durations in
the initial summary. Do not repeat a fact or add another question. A charging option remains
a suggestion until the driver asks to add it. For FASTEST, offer only returned
quick-charging options.
A reroute result alone confirms that the route changed and supplies its new
distance and duration. Mention a returned opportunity only when the driver
asks about it or it is clearly relevant; never call a suggestion confirmed.
A scenic preference is not a promise of scenery.

LOCATION AND VEHICLE
For "Where am I?" or a question about the car/current range, call
get_vehicle_context and report only relevant returned facts. For a car summary,
include the returned model, current range, and maximum range. Do not infer the
driver's location from the destination or make a Google request for this.
Never volunteer battery, range, consumption, or other telemetry unless asked.

PLACE SEARCH AND REROUTING
Use search_route_poi for requested hotels, restaurants, attractions, chargers,
coffee, rest, toilets, fuel, or service near the active route, a stop, or the
destination. Map sightseeing/landmarks to attraction, cafes to coffee, fuel/gas
stations to fuel, and restrooms to toilets. Use route, stop, or destination as
the requested location; never describe destination results as along-route
results.
For a hotel or restaurant request without a stated location, search near the
destination. Never override an explicitly requested route or stop location.
For a general charging question after planning, use the returned
chargingOptions. Search for more chargers only when the driver asks for a fresh
search or another location.

Search results are suggestions, not route changes. Use only returned names,
categories, tags/details, amenities, ratings/review counts, distances/detours,
and verified partner facts. Never invent review sentiment or facilities, and
do not repeat the same detail in different words. Offer no more than two hotels
or restaurants, and describe each in one short phrase using only returned
facts. Do not claim an option satisfies a preference unless the returned facts
support that. Offer no more than three attractions. For non-English place or
station names, use a concise English spoken rendering when its meaning is clear;
preserve proper names when they should not be translated. This rendering is
speech-only: keep the official returned name on the map and use original IDs
and names in every tool call. After the driver selects places, describe the
proposed change and ask for one confirmation for the selected set. A selection
alone is not confirmation. On clear acceptance, call reroute_through_poi once
with the returned stable IDs in selection order and the exact routeId/searchId,
and confirmation "confirmed". Do not invent or substitute IDs.

For nearby places at a charging stop, use search_stop_amenities with its exact
stopId and routeId (and searchId when supplied). Omit categories for a general
request. If there is no current charging stop, say one must be selected first.
This search is read-only. Report up to three returned results and their
verified facts. Do not invent facilities, opening hours, availability, ratings,
or benefits. If a returned name is difficult to pronounce, use a clear English
spoken rendering only when reliable; otherwise preserve the official name.

CHARGING AND ROUTE REQUIREMENTS
A direct request to add a charger or charging stop is sufficient consent; call
confirm_charging_stop immediately with the exact routeId and confirmation
"confirmed", without asking for another confirmation. This adds the complete
ordered charging plan as one action; never select or omit an individual
required stop or plan a second route. After success, first state every returned
station and its charging duration once, without discussing amenities or
announcing that you will check nearby. The app then focuses the map on the
first charging stop only when nearby places were returned, then requests a
brief continuation about those places. This is not a new search. Name each
distinct place once in one sentence beginning "Nearby you have". Do not add a
generic second clause such as "there are amenities nearby" or repeat the same
idea in different words. If empty, say none were found; if unavailable, say
they could not be checked. In both cases the map stays on the route overview.
Amenities are searched only around that first stop; later stops can be searched
if the driver asks. Never imply amenities were added to the route.
Mention partner benefits only when returned and verified. Do not claim that an
external merchant action has occurred unless a tool result confirms it.

For a returned vignette requirement, "buy the vignette" is sufficient consent.
Use its exact routeId/requirementId and confirmation "confirmed" without
asking twice or repeating the route requirement. Report only the returned
wallet status; never claim a third-party payment or say a confirmation was
sent to a phone app.

BOOKING AND DRIVING
Hotel/restaurant results are suggestions; naming or selecting one does not
book it. A clear request to book is sufficient consent. Preserve the returned
routeId/searchId/resultId, use bookingType hotel_room or restaurant_table, and
ask only for genuinely missing required date, time, or guest count. Resolve
"today" as the current local date, "tonight" as today at 20:00 for a
restaurant, and "tomorrow" as the next local date. Send spoken times as 24-hour
times (for example, 9 PM becomes 21:00). Never ask the driver to state a date
in a numeric date format or a time in military format. For bookings, report
the returned status once; never claim an external reservation or phone
notification, and never speak IDs.

On "Let's get going" or "Start driving", call start_driving with the current
routeId and confirmation "confirmed". Driving mode changes the presentation,
not the route. Report only returned progress, ETA, next stop, and charging
facts. To restore the full route, call return_to_main_route with the current
routeId; do not replan.

NUMBERS AND CLAIMS
Round route distances to whole kilometres; nearby-place distances remain in
metres and are rounded to the nearest 10 metres. Express durations in hours
and minutes. Speak prices only when returned by a tool, in EUR, without
hard-coded amounts. Use returned route alerts only for their stated location
and severity. A successful result is never a failure. Never invent or estimate
route, vehicle, charging, weather, border, toll, vignette, partner, price, or
place facts.
""".strip()
REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "get_vehicle_context",
        "description": (
            "Return the current configured vehicle location and authoritative "
            "vehicle/range facts. This is local cached data and makes no Google request."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "plan_route",
        "description": (
            "Plan a route from the configured vehicle origin to the driver's "
            "destination. Call this for a new route request."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "The driver's requested destination.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["FASTEST", "CHEAPEST", "SCENIC", "BALANCED"],
                    "description": (
                        "Required. Use FASTEST for fastest, quickest, or shortest-time; "
                        "CHEAPEST for lowest cost; SCENIC only when explicitly requested; "
                        "otherwise BALANCED. Never infer SCENIC."
                    ),
                },
            },
            "required": ["destination", "priority"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_route_poi",
        "description": (
            "Find factual POI suggestions near the active route, a selected "
            "stop, or the destination. Searching does not change the route."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "hotel", "restaurant", "attraction", "charging",
                        "coffee", "rest", "toilets", "fuel", "service",
                    ],
                    "description": (
                        "The kind of place requested. Use attraction for cool stuff, "
                        "sightseeing, landmarks, or interesting places; use coffee "
                        "for coffee stops or cafes; use fuel for fuel or gas stations; "
                        "use toilets for restrooms."
                    ),
                },
                "location": {
                    "type": "string",
                    "enum": ["route", "stop", "destination"],
                    "description": "Where the driver wants to search.",
                },
                "preference": {
                    "type": "string",
                    "description": "An optional preference such as Italian food or toilets.",
                },
            },
            "required": ["category", "location"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "reroute_through_poi",
        "description": (
            "Add one, two, or three previously suggested POIs as waypoints "
            "after the driver explicitly confirms the proposed reroute."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "poi_id": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
                    ],
                    "description": "One stable selected result ID, or an ordered array of up to three selected result IDs.",
                },
                "route_id": {
                    "type": "string",
                    "description": "The exact route_id returned with the selected search result.",
                },
                "search_id": {
                    "type": "string",
                    "description": "The exact search_id returned with the selected search result.",
                },
                "confirmation": {
                    "type": "string",
                    "enum": ["confirmed"],
                    "description": "Use exactly confirmed, and only after the driver clearly accepts the proposed route change.",
                },
            },
            "required": ["poi_id", "route_id", "search_id", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_stop_amenities",
        "description": (
            "Find factual amenities near the selected charging stop. This is "
            "read-only and does not change the route."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stopId": {
                    "type": "string",
                    "description": "The exact selected charging stop ID.",
                },
                "routeId": {
                    "type": "string",
                    "description": "The exact active route ID from the search context.",
                },
                "searchId": {
                    "type": ["string", "null"],
                    "description": "The exact search ID from the selected stop context, or null immediately after route planning.",
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "food", "coffee", "rest", "toilets", "shopping",
                            "hotel", "restaurant", "service",
                        ],
                    },
                    "maxItems": 4,
                    "description": "Optional amenity categories. Omit this field to search food, coffee, rest, and service nearby.",
                },
            },
            "required": ["stopId", "routeId", "searchId"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "confirm_charging_stop",
        "description": "Add every stop in the complete ordered charging plan as one action when the driver asks to add charging; do not ask for another confirmation. Amenities are returned for the first stop only.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "confirmation": {"type": "string", "enum": ["confirmed"]},
            },
            "required": ["routeId", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "purchase_vignette",
            "description": "Complete a vignette purchase after a clear driver request; confirmation is implicit.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "requirementId": {"type": "string"},
                "confirmation": {"type": "string", "enum": ["confirmed"]},
            },
            "required": ["routeId", "requirementId", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "book_hotel_room",
            "description": "Complete a hotel room booking after a clear driver request; confirmation is implicit.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "searchId": {"type": "string"},
                "resultId": {"type": "string"},
                "bookingType": {"type": "string", "enum": ["hotel_room"]},
                "guests": {"type": "integer", "minimum": 1, "maximum": 20},
                "date": {"type": "string", "description": "Normalized local date in YYYY-MM-DD. Convert today/tomorrow internally."},
                "confirmation": {"type": "string", "enum": ["confirmed"]},
            },
            "required": ["routeId", "searchId", "resultId", "bookingType", "guests", "date", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "book_restaurant_table",
            "description": "Complete a restaurant table booking after a clear driver request; confirmation is implicit.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "searchId": {"type": "string"},
                "resultId": {"type": "string"},
                "bookingType": {"type": "string", "enum": ["restaurant_table"]},
                "guests": {"type": "integer", "minimum": 1, "maximum": 20},
                "date": {"type": "string", "description": "Normalized local date in YYYY-MM-DD. Convert today/tomorrow internally."},
                "time": {"type": "string", "description": "Normalized local 24-hour time HH:MM. Convert phrases such as 9 PM internally."},
                "confirmation": {"type": "string", "enum": ["confirmed"]},
            },
            "required": ["routeId", "searchId", "resultId", "bookingType", "guests", "date", "time", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "start_driving",
        "description": "Activate presentation-only driving mode after explicit driver confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "confirmation": {"type": "string", "enum": ["confirmed"]},
            },
            "required": ["routeId", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "return_to_main_route",
        "description": "Restore the full-route presentation without replanning.",
        "parameters": {
            "type": "object",
            "properties": {"routeId": {"type": "string"}},
            "required": ["routeId"],
            "additionalProperties": False,
        },
    },
]


class RealtimeSessionProvider(Protocol):
    async def create_client_secret(self) -> str: ...


class OpenAIRealtimeProvider:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        secret_seconds: int = 600,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._secret_seconds = secret_seconds

    async def create_client_secret(self) -> str:
        if not self._api_key:
            raise APIError(
                503,
                "REALTIME_UNAVAILABLE",
                "Realtime voice is not configured.",
            )

        started_at = monotonic()
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self._api_key)
            response = await client.realtime.client_secrets.create(
                expires_after={
                    "anchor": "created_at",
                    "seconds": self._secret_seconds,
                },
                session={
                    "type": "realtime",
                    "model": self._model,
                    "instructions": REALTIME_INSTRUCTIONS,
                    "output_modalities": ["audio"],
                    "audio": {"output": {"voice": "marin"}},
                    "tools": REALTIME_TOOLS,
                    "tool_choice": "auto",
                    "max_output_tokens": 768,
                },
            )
        except APIError:
            raise
        except Exception as error:
            LOGGER.warning(
                "session_secret_request_ms=%d error=%s",
                round((monotonic() - started_at) * 1000),
                type(error).__name__,
            )
            raise APIError(
                503,
                "REALTIME_UNAVAILABLE",
                "The Realtime voice service is unavailable.",
            ) from error

        if not response.value:
            raise APIError(
                503,
                "REALTIME_UNAVAILABLE",
                "The Realtime voice service returned an invalid session.",
            )
        LOGGER.info(
            "session_secret_request_ms=%d",
            round((monotonic() - started_at) * 1000),
        )
        return response.value
