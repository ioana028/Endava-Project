from dataclasses import dataclass
from typing import Protocol

from ...models.contracts import AssistantIntent


@dataclass(frozen=True, slots=True)
class AIResult:
    transcript: str
    intent: AssistantIntent
    audio: bytes | None = None


class AssistantAIModule(Protocol):
    async def process_text(self, text: str, session_id: str | None) -> AIResult: ...

    async def process_voice(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        session_id: str | None,
    ) -> AIResult: ...