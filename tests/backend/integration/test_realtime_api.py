from typing import Any

from fastapi.testclient import TestClient

from backend.app.core.errors import APIError
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

    async def search_route_poi(
        self, category: str, location: str | None = None, preference: str | None = None
    ) -> list[Any]:
        return []

    async def search_stop_amenities(
        self,
        stop_id: str,
        route_id: str,
        search_id: str,
        categories: list[str],
    ) -> dict[str, Any]:
        del categories
        if stop_id != "charging-1":
            raise APIError(
                409,
                "STALE_STOP_CONTEXT",
                "That charging stop is no longer part of the active route.",
            )
        return {
            "selected_stop_name": "ChargePoint Parndorf",
            "results": [],
            "radius_meters": 500,
            "route_id": route_id,
            "search_id": search_id,
        }

    async def reroute_through_poi(
        self,
        poi_id: str,
        route_id: str,
        search_id: str,
        coords: tuple[float, float] | None = None,
        priority: Any = None,
    ) -> RouteResponse:
        del poi_id, route_id, search_id, coords, priority
        return await self.plan(type("Intent", (), {"destination": "Budapest"})())


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


def test_realtime_plan_route_defaults_to_balanced_priority() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/plan-route",
            json={"destination": "Budapest"},
        )

    assert response.status_code == 200
    assert response.json()["route"]["destination"] == "Budapest"


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


def test_health_config_reports_provider_presence_without_credentials() -> None:
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


def test_realtime_search_route_poi_returns_compact_contract() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/search-route-poi",
            json={"category": "fuel", "location": "route"},
        )

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_realtime_search_stop_amenities_returns_compact_contract() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/search-stop-amenities",
            json={
                "stopId": "charging-1",
                "routeId": "route-1",
                "searchId": "search-1",
                "categories": ["coffee", "food"],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "selectedStopName": "ChargePoint Parndorf",
        "results": [],
        "radiusMeters": 500,
        "routeId": "route-1",
        "searchId": "search-1",
    }


def test_realtime_search_stop_amenities_allows_initial_route_context() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/search-stop-amenities",
            json={
                "stopId": "charging-1",
                "routeId": "route-1",
            },
        )

    assert response.status_code == 200
    assert response.json()["selectedStopName"] == "ChargePoint Parndorf"
    assert response.json()["searchId"] is None


def test_realtime_search_stop_amenities_preserves_stale_error() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/search-stop-amenities",
            json={
                "stopId": "old-charging-stop",
                "routeId": "route-1",
                "searchId": "search-1",
                "categories": ["coffee"],
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STALE_STOP_CONTEXT"


def test_realtime_reroute_requires_explicit_confirmation() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/reroute-through-poi",
            json={
                "poiId": "poi-1",
                "routeId": "route-1",
                "searchId": "search-1",
                "confirmation": "maybe",
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_realtime_reroute_delegates_after_confirmation() -> None:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/reroute-through-poi",
            json={
                "poiId": "poi-1",
                "routeId": "route-1",
                "searchId": "search-1",
                "confirmation": "confirmed",
            },
        )

    assert response.status_code == 200
    assert response.json()["route"]["destination"] == "Budapest"


def test_realtime_reroute_reports_unavailable_service() -> None:
    app = create_app(
        route_service=object(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/reroute-through-poi",
            json={
                "poiId": "poi-1",
                "routeId": "route-1",
                "searchId": "search-1",
                "confirmation": "confirmed",
            },
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REROUTE_UNAVAILABLE"
