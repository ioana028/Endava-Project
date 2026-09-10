import base64
from typing import BinaryIO

from pydantic import ValidationError

from backend.app.integrations.openai.client import OpenAIClient
from backend.app.models.assistant import AssistantIntent, AssistantResponse


DAY_ONE_SPOKEN_RESPONSE = "Calculating route based on your preferences, hold on"


class AssistantProviderError(RuntimeError):
    """Raised when an external AI provider cannot complete an operation."""


class AssistantService:
    def __init__(self, client: OpenAIClient, synthesize_audio: bool = True) -> None:
        self._client = client
        self._synthesize_audio = synthesize_audio

    async def interact_text(self, text: str) -> AssistantResponse:
        if not text.strip():
            raise ValueError("text must contain non-whitespace content")

        try:
            raw_intent = await self._client.extract_intent(text)
            intent = AssistantIntent.model_validate(raw_intent)
        except ValidationError:
            raise
        except Exception as error:
            raise AssistantProviderError("intent extraction failed") from error

        audio_base64 = await self._synthesize()
        return AssistantResponse(
            transcript=text,
            intent=intent,
            spokenResponse=DAY_ONE_SPOKEN_RESPONSE,
            audioBase64=audio_base64,
            toastMessage=f"INTENT: {intent.destination.upper()} ({intent.priority})",
        )

    async def interact_voice(
        self, audio: BinaryIO, filename: str = "recording.webm"
    ) -> AssistantResponse:
        try:
            transcript = await self._client.transcribe(audio, filename)
        except Exception as error:
            raise AssistantProviderError("audio transcription failed") from error
        return await self.interact_text(transcript)

    async def _synthesize(self) -> str | None:
        if not self._synthesize_audio:
            return None

        try:
            audio_bytes = await self._client.synthesize(DAY_ONE_SPOKEN_RESPONSE)
        except Exception as error:
            raise AssistantProviderError("speech synthesis failed") from error
        return base64.b64encode(audio_bytes).decode("ascii")
