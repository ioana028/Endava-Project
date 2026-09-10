from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models.contracts import AssistantIntent, RoutePriority
from backend.app.services.assistant.ports import AIResult
from backend.app.services.assistant.service import LocalTextAIModule


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


def test_text_fallback_matches_frontend_contract() -> None:
    with TestClient(create_app(LocalTextAIModule())) as client:
        response = client.post(
            "/api/assistant/interact",
            json={"text": "Suzanne, take me to Budapest fast", "sessionId": "demo"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "transcript": "Suzanne, take me to Budapest fast",
        "intent": {"destination": "Budapest", "priority": "FASTEST"},
        "spokenResponse": "Calculating route based on your preferences, hold on",
        "toastMessage": "INTENT: BUDAPEST (FASTEST)",
    }


def test_voice_upload_is_forwarded_to_ai_module() -> None:
    ai_module = FakeAIModule()
    with TestClient(create_app(ai_module)) as client:
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
    assert response.json()["audioBase64"] == "bXAzLWRhdGE="
    assert "route" not in response.json()


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