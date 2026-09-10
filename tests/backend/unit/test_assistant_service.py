import asyncio
from io import BytesIO

import pytest

from backend.app.services.assistant import (
    DAY_ONE_SPOKEN_RESPONSE,
    AssistantProviderError,
    AssistantService,
)


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.transcribed_filename = None
        self.extracted_transcript = None
        self.synthesized_text = None

    async def transcribe(self, audio: BytesIO, filename: str) -> str:
        assert audio.read() == b"audio"
        self.transcribed_filename = filename
        return "Suzanne, take me to Budapest fast"

    async def extract_intent(self, transcript: str) -> dict[str, str]:
        self.extracted_transcript = transcript
        return {"destination": "Budapest", "priority": "FASTEST"}

    async def synthesize(self, text: str) -> bytes:
        self.synthesized_text = text
        return b"mp3-bytes"


def test_text_interaction_returns_day_one_response_and_audio() -> None:
    client = FakeOpenAIClient()
    response = asyncio.run(
        AssistantService(client).interact_text("Suzanne, take me to Budapest fast")
    )

    assert response.transcript == "Suzanne, take me to Budapest fast"
    assert response.intent.destination == "Budapest"
    assert response.intent.priority == "FASTEST"
    assert response.spoken_response == DAY_ONE_SPOKEN_RESPONSE
    assert response.audio_base64 == "bXAzLWJ5dGVz"
    assert response.route is None
    assert client.synthesized_text == DAY_ONE_SPOKEN_RESPONSE


def test_voice_interaction_transcribes_then_reuses_text_pipeline() -> None:
    client = FakeOpenAIClient()
    response = asyncio.run(
        AssistantService(client).interact_voice(BytesIO(b"audio"), "driver.webm")
    )

    assert response.transcript == "Suzanne, take me to Budapest fast"
    assert client.transcribed_filename == "driver.webm"
    assert client.extracted_transcript == response.transcript


def test_tts_can_be_disabled_for_text_fallback() -> None:
    response = asyncio.run(
        AssistantService(FakeOpenAIClient(), synthesize_audio=False).interact_text(
            "Take me to Budapest"
        )
    )

    assert response.audio_base64 is None


def test_blank_text_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-whitespace"):
        asyncio.run(AssistantService(FakeOpenAIClient()).interact_text("  "))


def test_provider_failure_is_wrapped() -> None:
    class FailingClient(FakeOpenAIClient):
        async def extract_intent(self, transcript: str) -> dict[str, str]:
            raise RuntimeError("provider unavailable")

    with pytest.raises(AssistantProviderError, match="intent extraction failed"):
        asyncio.run(
            AssistantService(FailingClient(), synthesize_audio=False).interact_text(
                "Take me to Budapest"
            )
        )
