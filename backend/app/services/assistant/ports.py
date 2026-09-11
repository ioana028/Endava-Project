from dataclasses import dataclass
from typing import Protocol

from ...models.contracts import AssistantIntent, RouteResponse


@dataclass(frozen=True, slots=True)
class AIResult:
    transcript: str
    intent: AssistantIntent
    audio: bytes | None = None


@dataclass(frozen=True, slots=True)
class RouteNarration:
    text: str
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

    async def synthesize_route(self, route: RouteResponse) -> RouteNarration: ...