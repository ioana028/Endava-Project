from typing import Any

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models.contracts import RouteResponse


class FakeRealtimeProvider:
    async def create_client_secret(self) -> str:
        return "ek_test_secret"


class FakeRouteService:
    async def plan(self, intent: Any) -> RouteResponse:
        return RouteResponse(
            origin="Vienna, Austria",
            destination=intent.destination,
            stats={
                "totalDistanceKm": 243,
                "totalDurationMinutes": 165,
                "totalPriceEur": 0,
            },
            geometry=[(16.37, 48.2), (19.04, 47.5)],
            stops=[],
            alerts=[],
        )


def test_realtime_session_returns_ephemeral_secret_and_model() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post("/api/assistant/realtime/session")

    assert response.status_code == 200
    assert response.json() == {
        "clientSecret": "ek_test_secret",
        "model": "gpt-realtime-2.1-mini",
    }


def test_realtime_plan_route_returns_structured_route() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/plan-route",
            json={"destination": "Budapest", "priority": "FASTEST"},
        )

    assert response.status_code == 200
    assert response.json()["route"]["destination"] == "Budapest"
    assert response.json()["route"]["stats"]["totalDurationMinutes"] == 165


def test_realtime_plan_route_rejects_unknown_priority() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/plan-route",
            json={"destination": "Budapest", "priority": "UNKNOWN"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
