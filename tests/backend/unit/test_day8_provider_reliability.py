from fastapi.testclient import TestClient

from backend.app.main import create_app


class FakeRealtimeProvider:
    async def create_client_secret(self) -> str:
        return "ek_test_secret"


class FakeRouteService:
    async def plan(self, *args, **kwargs):
        del args, kwargs
        raise AssertionError("Route planning should not run in this health check test")


def test_provider_health_handles_unavailable_partner_metadata(monkeypatch) -> None:
    def boom() -> object:
        raise RuntimeError("partner fixtures unavailable")

    monkeypatch.setattr("backend.app.main.FixtureRepository.load", boom)

    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.get("/health/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["partnerEnrichmentReady"] is False
    assert "placesProvider" in payload
