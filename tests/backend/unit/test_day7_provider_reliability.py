from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.models.contracts import RoutePriority
from backend.app.integrations.google_maps.routing import GoogleMapsRoutingProvider


class FakeRealtimeProvider:
    async def create_client_secret(self) -> str:
        return "ek_test_secret"


class FakeRouteService:
    async def plan(self, *args, **kwargs):
        del args, kwargs
        raise AssertionError("Route planning should not run in this provider-health test")


def test_provider_health_reports_scenic_and_partner_diagnostics() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.get("/health/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["placesProvider"] in {"google", "offline"}
    assert "googleServerApiKey" not in payload
    assert "openaiApiKey" not in payload
    assert "scenicCapability" in payload
    assert "partnerEnrichmentReady" in payload
    assert isinstance(payload["scenicCapability"], bool)
    assert isinstance(payload["partnerEnrichmentReady"], bool)


def test_google_routing_treats_scenic_as_distinct_from_fastest() -> None:
    provider = GoogleMapsRoutingProvider("test-key")

    assert provider._routing_preference(RoutePriority.FASTEST) == "TRAFFIC_AWARE_OPTIMAL"
    assert provider._routing_preference(RoutePriority.SCENIC) == "TRAFFIC_AWARE"
    assert provider._routing_preference(RoutePriority.SCENIC) != provider._routing_preference(RoutePriority.FASTEST)
