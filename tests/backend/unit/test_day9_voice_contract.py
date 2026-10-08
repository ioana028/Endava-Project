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
    normalized_instructions = " ".join(REALTIME_INSTRUCTIONS.split())
    assert "complete ordered charging plan as one action" in normalized_instructions
    assert "state every returned station and its charging duration once" in normalized_instructions
    assert "later stops can be searched if the driver asks" in normalized_instructions
    assert "no more than two hotels or restaurants" in normalized_instructions
    assert "speech-only" in normalized_instructions
    assert "At most one brief, noncommittal acknowledgement" in normalized_instructions
    assert "approximate travel time once" in normalized_instructions
    assert "route-average weather in plain language" in normalized_instructions
    assert "A direct request to add a charger or charging stop is sufficient consent" in normalized_instructions
    assert "brief continuation about those places" in normalized_instructions
    assert "Never ask the driver for an ID" in normalized_instructions
    assert 'acknowledgement is exactly "Got it."' in normalized_instructions
    assert "Never separately confirm wallet status" in normalized_instructions
    assert "Never repeat the charging station's benefit" in normalized_instructions
    assert "Never repeat the full route overview" in normalized_instructions
    assert "Google review rating strictly above 4.0" in normalized_instructions
    assert "latest explicit correction replaces the mistaken detail" in normalized_instructions
    assert "discard the rejected category and its suggestions" in normalized_instructions
    assert "Keep cuisine or facility preferences separate" in normalized_instructions
    assert "Chinese" not in REALTIME_INSTRUCTIONS
    assert '"Add charging", "add a charging stop", and "add charging stops"' in normalized_instructions
    assert "all mean confirm_charging_stop, never search_route_poi or plan_route" in normalized_instructions
    assert 'phoneConfirmationStatus is "simulated_sent"' in normalized_instructions
    assert "ask one short clarification instead of guessing" in normalized_instructions


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
