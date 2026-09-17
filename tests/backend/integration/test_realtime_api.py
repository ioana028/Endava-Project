from typing import Any

from fastapi.testclient import TestClient

from backend.app.core.errors import APIError
from backend.app.main import create_app
from backend.app.models.contracts import RouteResponse


class FakeRealtimeProvider:
    async def create_client_secret(self) -> str:
        return "ek_test_secret"


class FakeDay6Service:
    async def purchase_vignette(self, **payload: Any) -> dict[str, Any]:
        return {
            "status": "completed",
            "transaction_id": "txn-vignette-001",
            "route_id": payload["route_id"],
            "requirement_id": payload["requirement_id"],
            "wallet_status": "completed",
            "phone_confirmation_status": "sent",
            "amount_eur": 16.5,
            "currency": "EUR",
        }

    async def book_hotel_room(self, **payload: Any) -> dict[str, Any]:
        return {
            "status": "completed",
            "booking_id": "bk-hotel-001",
            "result_id": payload["result_id"],
            "route_id": payload["route_id"],
            "booking_type": payload["booking_type"],
            "guests": payload["guests"],
            "date": payload["date"],
            "time": payload.get("time"),
            "wallet_status": "completed",
            "phone_confirmation_status": "sent",
        }

    async def book_restaurant_table(self, **payload: Any) -> dict[str, Any]:
        result = await self.book_hotel_room(**payload)
        result["booking_id"] = "bk-restaurant-001"
        return result

    async def start_driving(self, **payload: Any) -> dict[str, Any]:
        return {
            "status": "active",
            "route_id": payload["route_id"],
            "remaining_distance_km": 184,
            "remaining_duration_minutes": 161,
            "eta": "14:35",
            "next_stop": {
                "id": "charging-1",
                "name": "TEA Mosonmagyarovar",
                "category": "charging",
            },
            "charging_required": True,
        }

    async def return_to_main_route(self, **payload: Any) -> dict[str, Any]:
        return {"status": "success", "route_id": payload["route_id"]}


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


def _day6_app() -> Any:
    app = create_app(
        route_service=FakeRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )
    app.state.commerce_service = FakeDay6Service()
    app.state.booking_service = app.state.commerce_service
    app.state.navigation_service = app.state.commerce_service
    return app


def test_realtime_day6_tools_return_camel_case_contracts() -> None:
    app = _day6_app()

    with TestClient(app) as client:
        purchase = client.post(
            "/api/assistant/realtime/tools/purchase-vignette",
            json={
                "routeId": "route-123",
                "requirementId": "hu-vignette-10d",
                "confirmation": "confirmed",
            },
        )
        hotel = client.post(
            "/api/assistant/realtime/tools/book-hotel-room",
            json={
                "routeId": "route-123",
                "searchId": "search-456",
                "resultId": "hotel-riverside",
                "bookingType": "hotel_room",
                "guests": 2,
                "date": "2026-09-17",
                "confirmation": "confirmed",
            },
        )
        restaurant = client.post(
            "/api/assistant/realtime/tools/book-restaurant-table",
            json={
                "routeId": "route-123",
                "searchId": "search-456",
                "resultId": "restaurant-italia",
                "bookingType": "restaurant_table",
                "guests": 2,
                "date": "2026-09-17",
                "time": "19:00",
                "confirmation": "confirmed",
            },
        )
        driving = client.post(
            "/api/assistant/realtime/tools/start-driving",
            json={"routeId": "route-123", "confirmation": "confirmed"},
        )
        returned = client.post(
            "/api/assistant/realtime/tools/return-to-main-route",
            json={"routeId": "route-123"},
        )

    assert purchase.status_code == hotel.status_code == restaurant.status_code == 200
    assert purchase.json()["transactionId"] == "txn-vignette-001"
    assert hotel.json()["bookingType"] == "hotel_room"
    assert restaurant.json()["bookingType"] == "restaurant_table"
    assert driving.json()["nextStop"]["name"] == "TEA Mosonmagyarovar"
    assert returned.json() == {"status": "success", "routeId": "route-123"}


def test_realtime_day6_tools_require_exact_confirmation() -> None:
    app = _day6_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/purchase-vignette",
            json={
                "routeId": "route-123",
                "requirementId": "hu-vignette-10d",
                "confirmation": "yes",
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
