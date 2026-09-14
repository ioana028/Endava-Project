from typing import Protocol

from ...core.errors import APIError


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
time. If a mandatory charging stop is returned, name it and say whether it is a partner location; include charging time only when returned. Never ask permission before a mandatory charging stop is added. Tell the driver to
purchase a vignette when that route requirement is returned. Mention a partner
benefit only when that exact benefit is returned. Do not explain calculations,
range comparisons, provider details, or repeated acknowledgements.

When the driver asks for a hotel, restaurant, attraction, charging stop,
coffee, rest, or service near the active route, a stop, or the destination,
call search_route_poi with the requested category, location, and preference.
Map "cool stuff to see", sightseeing, landmarks, and interesting places to
the attraction category. Map coffee stop, cafe, espresso, or a place for
coffee to the coffee category. For "along the route", use location route.
Searching returns suggestions only and does not change the route. Never say a
POI was added to the route unless a later tool result explicitly confirms a
reroute through it. Keep POI results concise and factual.

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
                        "coffee", "rest", "service",
                    ],
                    "description": (
                        "The kind of place requested. Use attraction for cool stuff, "
                        "sightseeing, landmarks, or interesting places; use coffee "
                        "for coffee stops or cafes."
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
        return response.value
