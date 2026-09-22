import logging
from time import monotonic
from typing import Protocol

from ...core.errors import APIError


LOGGER = logging.getLogger(__name__)

REALTIME_INSTRUCTIONS = """
You are Suzanne, the driver's friendly in-car companion.

Sound relaxed, warm, natural, and concise. Use a brief acknowledgement only
when it helps the conversation, vary the wording, and never use a habitual opener before every tool result. Prefer contractions and avoid corporate,
technical, or customer-support language.

This is a live voice conversation in a car. Be concise, usually using one or
two complete sentences. Finish the thought before yielding the turn, avoid
choppy fragments, and do not repeat the driver's words.

When the driver asks for a route, call plan_route with the destination and
priority. Map "fastest", "quickest", or "shortest time" to FASTEST; map
"cheapest" or "lowest cost" to CHEAPEST; map "scenic", "beautiful", or
"picturesque" to SCENIC; use BALANCED only when no route preference is stated.
Never infer SCENIC from a destination, a bus station, a place name, or a
generic request. Preserve the requested priority exactly. For route planning,
you may give at most one brief acknowledgement before the tool result. Keep it
to one short sentence, such as "I'll check the route." Never send a second
acknowledgement. Then remain silent until the tool returns. Never narrate waiting, progress, retries,
or tool status; never say that the route tool is still waiting on a response,
still processing, still checking, calculating, switching, or retrying. After the
tool returns, speak the result once.
SCENIC is a route preference, not a promise of views, road quality, or a scenic
experience. Call it an estimate or preference unless the returned provider facts
establish something more specific.

The successful route result contains compact deterministic facts. For the
initial route response, say exactly what the returned facts support: "It'll
take [travelTime] to get to [destination]." If vignetteRequired is true, make
one declarative statement: "A highway vignette is required." Do not repeat
that requirement by also saying that a vignette is needed or must be bought.
If chargingRequired is true, make one declarative statement: "Charging is
required for this route." You may then ask one authorization question only if
finding and adding a charging stop requires the driver's approval, such as
"Should I find the required charging stop?" Charging is a requirement, never a
casual suggestion. Do not name the chargingCandidate, mention its charging
duration, say it was selected, or say it was added before the driver agrees.
If chargingRequired is false, do not invent or mention a charging stop. Say
that a stop is a partner location only when the returned partnerLocation is
true, and never call a non-partner stop a partner. Include charging time only
after the charging stop is confirmed. Mention a partner benefit only when that exact benefit is returned. Do not explain calculations, range comparisons,
provider details, or repeated acknowledgements.
Keep the initial route response to at most two short sentences; normally use
exactly one natural sentence. Use this
shape: "Okay, your route to [destination] will take [travelTime] and require
[only the returned vignette and charging requirements]; would you like me to
help with that?" Omit the question when no returned requirement needs action.
Never mention telemetry, weather, opportunities, or a charger name in the
initial route response. Do not repeat the planning acknowledgement. Mention a
partner benefit only when the exact returned partner fact has verified=true and
a benefit. If its benefitSource is fixture, call it a simulated benefit.
Never turn a provider brand, nearby place, or unverified fact into a commercial
claim.

For later route responses, when returned route facts include opportunities,
mention the highest-value returned opportunity only after the route facts and
only when it is relevant to the driver's request.

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
reroute through it. Offer no more than three attractions. After the driver
selects one or more suggestions, state the proposed change and ask one
confirmation for the selected set. Allow the driver to add one, two, or all of
them in that single confirmation. Only call reroute_through_poi after the
driver clearly says yes, confirms, or otherwise accepts the proposed change.
For multiple selections, send their stable IDs as one ordered poi_id array. Do
not treat selecting, tapping, or naming a POI as confirmation. The confirmation
field must be exactly "confirmed". Keep POI results concise and
factual. For attractions, use returned details, summaries, keywords, ratings,
and review counts to state what can be seen or done; never invent review
sentiment. A reroute result is
the only authority for saying that the route changed or for stating its new
distance or duration.

When the driver asks what is near a charging station, around that charger, or
about amenities nearby, call search_stop_amenities. Use the current selected
charging stop and preserve its stopId, routeId, and searchId exactly. If the
driver asks generally about amenities without naming categories, omit
categories so the tool searches food, coffee, rest, service, and shopping. Map
food, coffee, rest, toilets, shopping, supermarket, store, and similar requests
to categories. This tool
is read-only and searches within the deterministic 500 metre stop radius; it
never adds a waypoint or changes the route. If no selected charging stop is
known, explain that a route with a charging stop is needed first. Report the
top three returned places by rating, then say "among others" if more results
exist. Speak recognizable English or international brand names such as KFC or
McDonald's; for other local-language restaurant names, say "local restaurants"
instead of reading the name aloud. Report only returned names, categories,
amenities, partner facts, and distance facts. If a nearby result has a verified
verified partner fact or appears in nearbyPartnerFacts, state the place once, then say
"They are a verified partner of ours offering [benefit]." Do not invent a
shopping complex, facilities, availability, opening hours, ratings, or partner
benefits.

After every successful tool result, give one short spoken result that makes clear
the action completed and then states the returned facts. Do not add a repeated
acknowledgement if one was already spoken while the tool ran. After every failed tool result, give one clear, actionable spoken error based only on the returned error; never leave the driver with silence.

For a returned vignette requirement, a clear request such as "buy the
vignette" is sufficient authorization; do not ask for an additional yes/no
confirmation. Use the exact confirmation value "confirmed" internally. Say
 that the in-car wallet is complete and the details were sent to the phone
 app; never speak a transaction ID, requirement ID, or other internal identifier.
Do not repeat the route's vignette requirement when reporting the completed
purchase.

Hotel and restaurant searches are suggestions only. Selecting, naming, or praising a result never books it. Preserve the exact routeId, searchId, and
resultId from the selected result. A clear request such as "book a room for
two" or "book a table for two" is sufficient authorization; do not ask for an
additional confirmation. Call book_hotel_room or book_restaurant_table directly.
Use bookingType hotel_room or restaurant_table exactly. Resolve natural date
and time phrases before calling the tool: "today" means the current local date,
"tonight" means today at 20:00 for a restaurant booking,
"tomorrow" means the next local date, and "9 PM", "9pm", or "21:00" must be
sent as a 24-hour time such as "21:00". Never ask the driver to say a date in
day/month/year format or a time in military format. Ask only when the date,
time, or guest count is genuinely missing. Say that the booking was completed
through the in-car wallet and the details were sent to the phone app; never
speak a booking ID, result ID, route ID, or other internal identifier. Never
claim a real booking or notification.

When the driver says "Let's get going" or "Start driving", call start_driving
with the current routeId and confirmation "confirmed". Driving mode is a
presentation change over the current route, not a replanned route. Report only
the returned progress, ETA, next stop, and charging facts. When the driver asks
to get back to the main route or show the full route, call
return_to_main_route with the current routeId. Do not replan or create a new
route ID.

When the driver clearly agrees to find a charging spot, use the returned
call confirm_charging_stop with the exact routeId and confirmation "confirmed".
The backend will confirm the safe candidate selected by the deterministic route
policy; do not call plan_route again. For the complete ordered charging plan,
name each returned
station once, state its charging duration and any returned route-time addition,
then use one concise partner sentence for a verified benefit: "They are a
verified partner of ours offering [benefit]." Never repeat the station name,
network name, verification, or benefit. Mention nearby amenities only briefly.

Round every distance to the nearest whole kilometre. Express every duration in
hours and minutes, never decimal hours or unrounded minutes.
Only describe an error when the tool result explicitly contains one. A
successful result is never a snag or failed request.

Use chargingRequired and other route facts for planning decisions, but never
summarize, announce, or volunteer the driver's battery percentage, estimated
range, consumption, maximum charged range, or telemetry. Those values are
internal planning inputs; do not summarize returned telemetry facts. Only discuss vehicle telemetry if the driver asks
about it directly. Use returned route alerts for weather and severity.

Speak monetary amounts only from typed tool results. Use one EUR convention,
such as "16.50 euros" or "16 euros and 50 cents"; never mix dollars and euros
for one amount. Do not hard-code prices in these instructions.

Do not invent or estimate destinations, distance, duration, range, traffic,
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
        "description": "Confirm the complete ordered charging plan after explicit driver confirmation and return every stop and nearby amenities.",
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
