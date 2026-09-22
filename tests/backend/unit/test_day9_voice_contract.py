from fastapi.testclient import TestClient

from backend.app.integrations.openai.realtime import REALTIME_INSTRUCTIONS
from backend.app.main import create_app
from backend.app.models.contracts import (
    ChargingPlan,
    RouteResponse,
    StopPinpoint,
    TelemetryNarrationFacts,
    TripStats,
)


class FakeRealtimeProvider:
    async def create_client_secret(self) -> str:
        return "ek_test_secret"


class OpportunityRouteService:
    async def search_route_poi(self, **kwargs):
        del kwargs
        return {
            "results": [
                StopPinpoint(
                    id="attraction-1",
                    name="Danube Panorama",
                    category="attraction",
                    coords=(17.0, 48.0),
                    tag="Riverside viewpoint",
                    details="Views of the river and historic bridges.",
                    rating=4.8,
                    user_review_count=240,
                )
            ],
            "opportunities": [],
        }


class MinimalRouteService:
    async def search_route_poi(self, **kwargs):
        del kwargs
        return []


def test_day9_contract_keeps_voice_safe_route_facts() -> None:
    stop = StopPinpoint(
        id="charger-1",
        name="Shell Recharge",
        category="charging",
        coords=(17.0, 48.0),
        charging_duration_minutes=28,
    )
    route = RouteResponse(
        origin="Vienna",
        destination="Budapest",
        stats=TripStats(total_distance_km=240, total_duration_minutes=190),
        geometry=[(16.0, 48.0), (19.0, 47.5)],
        stops=[stop],
        telemetry=TelemetryNarrationFacts(
            battery_percent=42,
            estimated_range_km=120,
            max_charged_range_km=280,
            consumption_rate_kwh=16,
            charging_feasible=True,
        ),
        charging_plan=ChargingPlan(
            stops=[stop],
            complete=True,
            total_charging_minutes=28,
            confirmed=True,
        ),
    )

    assert route.telemetry is not None
    assert route.telemetry.estimated_range_km == 120
    assert route.charging_plan is not None
    assert route.charging_plan.stops[0].id == "charger-1"


def test_day9_realtime_instructions_are_statement_first_and_complete() -> None:
    assert "suzanne:connection-confirmed" not in REALTIME_INSTRUCTIONS
    assert "complete ordered charging plan" in REALTIME_INSTRUCTIONS
    assert "returned telemetry facts" in REALTIME_INSTRUCTIONS
    assert "route alerts" in REALTIME_INSTRUCTIONS
    assert "review counts" in REALTIME_INSTRUCTIONS
    assert "verified partner fact" in REALTIME_INSTRUCTIONS
    assert "speak the result once" in REALTIME_INSTRUCTIONS
    assert "at most one brief acknowledgement" in REALTIME_INSTRUCTIONS
    assert "still waiting on a response" in REALTIME_INSTRUCTIONS
    assert "Charging is a requirement, never a" in REALTIME_INSTRUCTIONS
    assert "Do not repeat the route's vignette requirement" in REALTIME_INSTRUCTIONS


def test_route_poi_api_preserves_service_opportunities() -> None:
    app = create_app(
        route_service=OpportunityRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/search-route-poi",
            json={"category": "attraction", "location": "route"},
        )

    assert response.status_code == 200
    assert response.json()["results"][0]["details"] == "Views of the river and historic bridges."
    assert response.json()["results"][0]["userReviewCount"] == 240
    assert response.json()["opportunities"] == []


def test_route_poi_api_keeps_empty_service_results_compatible() -> None:
    app = create_app(
        route_service=MinimalRouteService(),
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/search-route-poi",
            json={"category": "attraction", "location": "route"},
        )

    assert response.status_code == 200
    assert response.json()["results"] == []
