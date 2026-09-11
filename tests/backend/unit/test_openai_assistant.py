import asyncio

from backend.app.integrations.openai.assistant import (
    OpenAIAssistantModule,
    build_route_narration,
)
from backend.app.models.contracts import (
    AssistantIntent,
    RoutePriority,
    RouteResponse,
    TripStats,
)


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.transcription_language: str | None = None
        self.synthesized_text: str | None = None

    async def transcribe(self, audio, filename: str, language: str = "en") -> str:
        assert audio.read() == b"audio"
        assert filename == "request.webm"
        self.transcription_language = language
        return "Suzanne, take me to Budapest fast"

    async def extract_intent(self, transcript: str) -> dict[str, str]:
        assert transcript == "Suzanne, take me to Budapest fast"
        return {"destination": "Budapest", "priority": "FASTEST"}

    async def synthesize(self, text: str) -> bytes:
        self.synthesized_text = text
        return b"route-audio"


def route_with_alert() -> RouteResponse:
    return RouteResponse(
        origin="Vienna, Austria",
        destination="Budapest",
        stats=TripStats(total_distance_km=243, total_duration_minutes=165),
        geometry=[(16.37, 48.2), (19.04, 47.5)],
        alerts=[
            {
                "type": "VEHICLE",
                "severity": "WARNING",
                "message": (
                    "Your car has an estimated range of 95 km and cannot cover "
                    "this distance. Should I add a charging stop for you?"
                ),
            }
        ],
    )


def test_route_narration_uses_structured_facts_and_one_charging_question() -> None:
    narration = build_route_narration(route_with_alert())

    assert narration == (
        "I've planned your route to Budapest. It's 243 kilometres and it will "
        "take approximately 2 hours 45 minutes. Your car has an estimated "
        "range of 95 km and cannot cover this distance. Should I add a charging "
        "stop for you?"
    )
    assert narration.count("Should I add a charging stop for you?") == 1


def test_route_narration_omits_charging_question_when_range_is_sufficient() -> None:
    route = route_with_alert().model_copy(update={"alerts": []})

    assert build_route_narration(route) == (
        "I've planned your route to Budapest. It's 243 kilometres and it will "
        "take approximately 2 hours 45 minutes."
    )


def test_process_text_does_not_generate_backend_filler_audio() -> None:
    client = FakeOpenAIClient()
    result = asyncio.run(
        OpenAIAssistantModule(client).process_text(
            "Suzanne, take me to Budapest fast", "demo"
        )
    )

    assert result.audio is None
    assert client.synthesized_text is None


def test_fake_openai_client_handles_english_voice_and_route_tts() -> None:
    client = FakeOpenAIClient()
    module = OpenAIAssistantModule(client)

    result = asyncio.run(
        module.process_voice(b"audio", "request.webm", "audio/webm", "demo")
    )
    narration, audio = asyncio.run(module.synthesize_route(route_with_alert()))

    assert result.transcript == "Suzanne, take me to Budapest fast"
    assert result.intent == AssistantIntent(
        destination="Budapest", priority=RoutePriority.FASTEST
    )
    assert client.transcription_language == "en"
    assert narration == client.synthesized_text
    assert audio == b"route-audio"