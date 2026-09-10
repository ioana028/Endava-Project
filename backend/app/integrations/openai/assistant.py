import io

from ...models.contracts import AssistantIntent
from ...services.assistant.ports import AIResult
from .client import OpenAIClient


class OpenAIAssistantModule:
    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    async def process_text(self, text: str, session_id: str | None) -> AIResult:
        del session_id
        intent = AssistantIntent.model_validate(await self._client.extract_intent(text))
        audio = await self._client.synthesize(
            "Calculating route based on your preferences, hold on"
        )
        return AIResult(transcript=text, intent=intent, audio=audio)

    async def process_voice(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        session_id: str | None,
    ) -> AIResult:
        del content_type
        transcript = await self._client.transcribe(io.BytesIO(audio), filename)
        result = await self.process_text(transcript, session_id)
        return AIResult(transcript=transcript, intent=result.intent, audio=result.audio)