from typing import Any, BinaryIO, Protocol


class OpenAIClient(Protocol):
    async def transcribe(self, audio: BinaryIO, filename: str) -> str:
        ...

    async def extract_intent(self, transcript: str) -> dict[str, str]:
        ...

    async def synthesize(self, text: str) -> bytes:
        ...


class AsyncOpenAIClient:
    """OpenAI adapter; provider response shapes stay outside application code."""

    def __init__(self, api_key: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio: BinaryIO, filename: str) -> str:
        result = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio),
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
        tool_call = response.choices[0].message.tool_calls[0]
        arguments: Any = tool_call.function.arguments
        if isinstance(arguments, str):
            import json

            arguments = json.loads(arguments)
        return arguments

    async def synthesize(self, text: str) -> bytes:
        response = await self._client.audio.speech.create(
            model="tts-1",
            voice="sage",
            input=text,
            response_format="mp3",
        )
        return await response.aread()
