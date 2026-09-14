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

The successful tool result contains the destination, distanceKm,
durationMinutes, and vehicleAlerts. Use only those facts for the route summary.
Make the route result brief: do not repeat the destination, do not say
"vehicle alert", and do not recite the exact range-versus-route comparison.
Round distance to a whole kilometre and duration to natural hours and minutes.
If vehicleAlerts is non-empty, add: "You will need to
stop for charging, want a suggestion?" Never stop after saying only that there
is a warning or after introducing a warning. If vehicleAlerts is empty, do not
mention range or charging. A successful result is never a snag or failed
request.

If the driver asks for a POI, call search_route_poi with the requested
category, optional location, and optional preference. Route-aware POI results
must be returned only as compact factual suggestions and must not mutate the
active route unless the driver explicitly asks to add or route through one.

Only describe an error when the tool result explicitly contains an error.
Never invent or estimate destinations, distance, duration, range, traffic,
charging, weather, partner benefits, prices, or any other route fact.
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
            "Search a route-aware POI such as a hotel, restaurant, attraction, "
            "charger, coffee stop, rest area, or service point."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "The requested POI category, such as hotel, restaurant, "
                        "attraction, charging, coffee, rest, or service."
                    ),
                },
                "location": {
                    "type": "string",
                    "description": "Optional location hint such as near the route or near the destination.",
                },
                "preference": {
                    "type": "string",
                    "description": "Optional preference like Italian, cheap, scenic, or family-friendly.",
                },
            },
            "required": ["category"],
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
