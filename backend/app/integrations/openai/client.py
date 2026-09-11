import json
from typing import Any, BinaryIO, Protocol

from ...core.errors import APIError


class OpenAIClient(Protocol):
    async def transcribe(
        self, audio: BinaryIO, filename: str, language: str = "en"
    ) -> str:
        ...

    async def extract_intent(self, transcript: str) -> dict[str, str]:
        ...

    async def narrate_route(self, route_facts: dict[str, Any]) -> str:
        ...

    async def synthesize(self, text: str) -> bytes:
        ...


class AsyncOpenAIClient:
    """OpenAI adapter; provider response shapes stay outside application code."""

    def __init__(self, api_key: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)

    async def transcribe(
        self, audio: BinaryIO, filename: str, language: str = "en"
    ) -> str:
        result = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio),
            language=language,
        )
        return result.text

    async def extract_intent(self, transcript: str) -> dict[str, str]:
        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract the driver's destination and route priority. "
                        "Priority must be FASTEST, CHEAPEST, SCENIC, or BALANCED. "
                        "Return only the requested function arguments."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "extract_route_intent",
                        "description": "Extract destination and route priority.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "destination": {"type": "string"},
                                "priority": {
                                    "type": "string",
                                    "enum": [
                                        "FASTEST",
                                        "CHEAPEST",
                                        "SCENIC",
                                        "BALANCED",
                                    ],
                                },
                            },
                            "required": ["destination", "priority"],
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_route_intent"},
            },
        )
        if not response.choices or not response.choices[0].message.tool_calls:
            raise APIError(
                503,
                "AI_UNAVAILABLE",
                "The assistant could not extract a route intent.",
            )
        tool_call = response.choices[0].message.tool_calls[0]
        arguments: Any = tool_call.function.arguments
        if isinstance(arguments, str):
            import json

            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as error:
                raise APIError(
                    503,
                    "AI_UNAVAILABLE",
                    "The assistant returned an invalid route intent.",
                ) from error
        if not isinstance(arguments, dict):
            raise APIError(
                503,
                "AI_UNAVAILABLE",
                "The assistant returned an invalid route intent.",
            )
        return arguments

    async def synthesize(self, text: str) -> bytes:
        response = await self._client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
            response_format="mp3",
        )
        return await response.aread()

    async def narrate_route(self, route_facts: dict[str, Any]) -> str:
        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Suzanne, a concise, warm in-car route assistant. "
                        "Narrate only the supplied route facts. Mention destination, "
                        "distance, and duration. If a vehicle alert says charging "
                        "may be required, explain that fact and ask whether the "
                        "driver wants a charging option. Never invent a station, "
                        "price, review, weather detail, or route fact. Return only "
                        "the spoken response in English, under 45 words."
                    ),
                },
                {"role": "user", "content": json.dumps(route_facts)},
            ],
        )
        if not response.choices:
            raise APIError(
                503,
                "AI_UNAVAILABLE",
                "The assistant could not narrate the route.",
            )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise APIError(
                503,
                "AI_UNAVAILABLE",
                "The assistant could not narrate the route.",
            )
        return content.strip()
