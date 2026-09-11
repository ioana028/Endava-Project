import asyncio

import pytest

from backend.app.core.errors import APIError
from backend.app.models.contracts import AssistantIntent, RoutePriority, RouteResponse, TripStats
from backend.app.services.assistant.ports import AIResult, RouteNarration
from backend.app.services.assistant.service import (
    AssistantService,
    DAY_ONE_SPOKEN_RESPONSE,
    LocalTextAIModule,
)


class FakeAIModule:
    async def process_text(self, text: str, session_id: str | None) -> AIResult:
        del session_id
        return AIResult(
            transcript=text,
            intent=AssistantIntent(
                destination="Budapest",
                priority=RoutePriority.FASTEST,
            ),
        )

    async def process_voice(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        session_id: str | None,
    ) -> AIResult:
        del audio, filename, content_type, session_id
        return AIResult(
            transcript="Suzanne, take me to Budapest fast",
            intent=AssistantIntent(
                destination="Budapest",
                priority=RoutePriority.FASTEST,
            ),
        )

    async def synthesize_route(self, route: RouteResponse) -> RouteNarration:
        return RouteNarration(text=f"Route to {route.destination} is ready.")


def test_text_fallback_preserves_day_one_response_without_route_service() -> None:
    response = asyncio.run(
        AssistantService(LocalTextAIModule()).interact(
            "Suzanne, take me to Budapest fast",
            "demo",
        )
    )

    assert response.transcript == "Suzanne, take me to Budapest fast"
    assert response.intent.destination == "Budapest"
    assert response.intent.priority == RoutePriority.FASTEST
    assert response.spoken_response == DAY_ONE_SPOKEN_RESPONSE
    assert response.route is None


def test_assistant_service_uses_fake_ai_module() -> None:
    response = asyncio.run(
        AssistantService(FakeAIModule()).interact(
            "Suzanne, take me to Budapest fast",
            "demo",
        )
    )

    assert response.intent == AssistantIntent(
        destination="Budapest",
        priority=RoutePriority.FASTEST,
    )


def test_blank_text_is_rejected() -> None:
    with pytest.raises(APIError) as error:
        asyncio.run(AssistantService(LocalTextAIModule()).interact("  ", "demo"))

    assert error.value.code == "INVALID_REQUEST"
