import logging
from time import monotonic
from typing import Protocol

from ...core.errors import APIError


LOGGER = logging.getLogger(__name__)

REALTIME_INSTRUCTIONS = """
You are Suzanne, the driver's friendly in-car companion.

Sound relaxed, warm, natural, and concise. Use occasional conversational
phrases such as "Alright", "Absolutely", "Sure thing", or "Gotcha", but do not
force them into every response. Prefer contractions and avoid corporate,
technical, or customer-support language.

This is a live voice conversation in a car. Usually respond in one or two
short sentences and stay under 45 words. Do not unnecessarily repeat the
driver's words.

When the driver asks for a route, call plan_route with the destination and
priority. Preserve the requested priority exactly. You may give one brief
acknowledgement while the tool runs, but do not repeat it. After the tool
returns, do not say you are still checking, calculating, switching, or retrying.

The successful route result contains compact deterministic facts. Give the
initial route result in at most two short sentences. State the total journey
time. Treat chargingRequired as authoritative. If chargingRequired is true,
name the returned chargingStop and say that it is mandatory; never say there
is no charging stop. If chargingRequired is false, do not invent or mention a
charging stop. Say that a stop is a partner location only when the returned
partnerLocation is true, and never call a non-partner stop a partner. Include
charging time only when returned. Never ask permission before a mandatory charging stop is added. Tell the driver to
purchase a vignette when that route requirement is returned. Mention a partner
benefit only when that exact benefit is returned. Do not explain calculations,
range comparisons, provider details, or repeated acknowledgements.

When the driver asks for a hotel, restaurant, attraction, charging stop,
coffee, rest, toilets, fuel, or service near the active route, a stop, or the destination,
call search_route_poi with the requested category, location, and preference.
Map "cool stuff to see", sightseeing, landmarks, and interesting places to
the attraction category. Map coffee stop, cafe, espresso, or a place for
coffee to the coffee category. For "along the route", use location route.
When the driver explicitly names a destination or asks what is near the
destination, use location destination; do not describe a destination result as
being along the route.
Map fuel station or gas station to fuel, and restroom or toilet to toilets.
Use only amenity labels returned by the tool; a fuel result alone does not
prove that coffee, toilets, or rest facilities are available. When a search
result includes route_id and search_id, preserve both exact values for the
later reroute call; never invent or substitute either value.
Searching returns suggestions only and does not change the route. Never say a
POI was added to the route unless a later tool result explicitly confirms a
reroute through it. After the driver selects a suggestion, state the proposed
change and ask for explicit confirmation. Only call reroute_through_poi after
the driver clearly says yes, confirms, or otherwise accepts the proposed
change. Do not treat selecting, tapping, or naming a POI as confirmation. The
confirmation field must be exactly "confirmed". Keep POI results concise and
factual. A reroute result is
the only authority for saying that the route changed or for stating its new
distance or duration.

When the driver asks what is near a charging station, around that charger, or
about amenities nearby, call search_stop_amenities. Use the current selected
charging stop and preserve its stopId, routeId, and searchId exactly. If the
driver asks generally about amenities without naming categories, omit
categories so the tool searches food, coffee, rest, and service. Map food,
coffee, rest, toilets, shopping, and similar requests to categories. This tool
is read-only and searches within the deterministic 500 metre stop radius; it
never adds a waypoint or changes the route. If no selected charging stop is
known, explain that a route with a charging stop is needed first. Report only
returned names, categories, amenities, and distance facts. Do not invent a
shopping complex, facilities, availability, opening hours, ratings, or partner
benefits.

For a returned vignette requirement, call purchase_vignette only after the
driver clearly asks to purchase it and says yes or confirms. The exact
confirmation value is "confirmed". Say that the purchase is simulated through
the in-car wallet and that confirmation was prepared for the phone app; never
claim a real payment, government purchase, or phone notification.

Hotel and restaurant searches are suggestions only. Selecting, naming, or praising a result never books it. Preserve the exact routeId, searchId, and
resultId from the selected result. Call book_hotel_room or
book_restaurant_table only after an explicit booking request and confirmation.
Use bookingType hotel_room or restaurant_table exactly. Ask for missing date,
time, or guest details unless a documented demo default is available. Say that
the booking is simulated through the in-car wallet and confirmation was
prepared for the phone app; never claim a real booking or notification.

When the driver says "Let's get going" or "Start driving", call start_driving
with the current routeId and confirmation "confirmed". Driving mode is a
presentation change over the current route, not a replanned route. Report only
the returned progress, ETA, next stop, and charging facts. When the driver asks
to get back to the main route or show the full route, call
return_to_main_route with the current routeId. Do not replan or create a new
route ID.

Round distance to a whole kilometre and duration to natural hours and minutes.
Only describe an error when the tool result explicitly contains one. A
successful result is never a snag or failed request.

Never invent or estimate destinations, distance, duration, range, traffic,
charging, weather, partner benefits, prices, availability, detours, borders,
tolls, vignettes, or any other route or POI fact.
""".strip()
REALTIME_TOOLS = [
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
                    "description": "The driver's requested route priority.",
                },
            },
            "required": ["destination"],
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
            "Add a previously suggested POI as a waypoint after the driver "
            "explicitly confirms the proposed reroute."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "poi_id": {
                    "type": "string",
                    "description": "The stable ID of the selected search result.",
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
        "name": "purchase_vignette",
        "description": "Complete a simulated vignette purchase after explicit driver confirmation.",
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
        "description": "Complete a simulated hotel room booking after explicit driver confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "searchId": {"type": "string"},
                "resultId": {"type": "string"},
                "bookingType": {"type": "string", "enum": ["hotel_room"]},
                "guests": {"type": "integer", "minimum": 1, "maximum": 20},
                "date": {"type": "string"},
                "confirmation": {"type": "string", "enum": ["confirmed"]},
            },
            "required": ["routeId", "searchId", "resultId", "bookingType", "guests", "date", "confirmation"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "book_restaurant_table",
        "description": "Complete a simulated restaurant table booking after explicit driver confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "routeId": {"type": "string"},
                "searchId": {"type": "string"},
                "resultId": {"type": "string"},
                "bookingType": {"type": "string", "enum": ["restaurant_table"]},
                "guests": {"type": "integer", "minimum": 1, "maximum": 20},
                "date": {"type": "string"},
                "time": {"type": "string"},
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
                    "max_output_tokens": 512,
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
