from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.core.fixture_repository import FixtureRepository
from backend.app.main import create_app
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority
from backend.app.services.assistant.ports import AIResult, RouteNarration
from backend.app.services.assistant.service import LocalTextAIModule
from backend.app.services.trip.ports import GeocodedPlace, ProviderRoute
from backend.app.services.trip.service import RouteService


class FakeRoutingProvider:
    async def geocode(self, place: str) -> GeocodedPlace:
        return GeocodedPlace(
            display_name=place,
            coordinates=Coordinates(lng=16.37, lat=48.20),
        )

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
    ) -> ProviderRoute:
        del origin, destination, priority
        return ProviderRoute(
            distance_meters=243_000,
            duration_seconds=9_900,
            geometry=((16.37, 48.20), (19.04, 47.50)),
        )


def fake_route_service() -> RouteService:
    repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"),
        Path("data/partners/partners.json"),
    )
    repository.load()
    return RouteService(FakeRoutingProvider(), repository)


class FakeAIModule:
    def __init__(self) -> None:
        self.voice_call: tuple[bytes, str, str, str | None] | None = None

    async def process_text(self, text: str, session_id: str | None) -> AIResult:
        return AIResult(
            transcript=text,
            intent=AssistantIntent(
                destination="Budapest", priority=RoutePriority.FASTEST
            ),
        )

    async def process_voice(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        session_id: str | None,
    ) -> AIResult:
        self.voice_call = (audio, filename, content_type, session_id)
        return AIResult(
            transcript="Suzanne, take me to Budapest fast",
            intent=AssistantIntent(
                destination="Budapest", priority=RoutePriority.FASTEST
            ),
            audio=b"mp3-data",
        )

    async def synthesize_route(self, route) -> RouteNarration:
        return RouteNarration(
            text=f"Route to {route.destination} is ready.",
            audio=b"route-audio",
        )


def test_text_fallback_matches_frontend_contract() -> None:
    with TestClient(
        create_app(LocalTextAIModule(), route_service=fake_route_service())
    ) as client:
        response = client.post(
            "/api/assistant/interact",
            json={"text": "Suzanne, take me to Budapest fast", "sessionId": "demo"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "Suzanne, take me to Budapest fast"
    assert payload["intent"] == {"destination": "Budapest", "priority": "FASTEST"}
    assert payload["spokenResponse"].startswith("I've planned your route to")
    assert payload["toastMessage"] == "INTENT: BUDAPEST (FASTEST)"
    assert payload["route"] is not None
    assert payload["route"]["destination"].startswith("Budapest")
    assert payload["route"]["stats"]["totalDistanceKm"] > 0
    assert payload["route"]["stats"]["totalDurationMinutes"] > 0
    assert payload["route"]["geometry"]


def test_voice_upload_is_forwarded_to_ai_module() -> None:
    ai_module = FakeAIModule()
    with TestClient(
        create_app(ai_module, route_service=fake_route_service())
    ) as client:
        response = client.post(
            "/api/assistant/voice",
            files={"audio": ("request.webm", b"audio-data", "audio/webm")},
            data={"sessionId": "demo-session"},
        )

    assert response.status_code == 200
    assert ai_module.voice_call == (
        b"audio-data",
        "request.webm",
        "audio/webm",
        "demo-session",
    )
    payload = response.json()
    assert payload["audioBase64"] == "cm91dGUtYXVkaW8="
    assert payload["route"] is not None
    assert payload["route"]["destination"].startswith("Budapest")


def test_fixtures_are_loaded_and_validated_at_startup() -> None:
    app = create_app(LocalTextAIModule())
    with TestClient(app):
        assert app.state.fixtures.telemetry.vehicle_id == "honda-e-demo"
        assert len(app.state.fixtures.partners) == 3


def test_invalid_audio_uses_stable_error_envelope() -> None:
    with TestClient(create_app(LocalTextAIModule())) as client:
        response = client.post(
            "/api/assistant/voice",
            files={"audio": ("request.txt", b"not-audio", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AUDIO"
    assert response.json()["error"]["requestId"]