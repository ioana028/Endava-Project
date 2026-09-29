from typing import Any

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from backend.app.integrations.openai.realtime import REALTIME_INSTRUCTIONS, REALTIME_TOOLS
from backend.app.main import create_app
from backend.app.models.contracts import (
    RealtimeToolStartDrivingRequest,
    RealtimeToolStartDrivingResponse,
)


class FakeRealtimeProvider:
    async def create_client_secret(self) -> str:
        return "ek_test_secret"


class FakeRouteService:
    def __init__(self) -> None:
        self.start_driving_payload: dict[str, Any] | None = None

    async def start_driving(self, **payload: Any) -> dict[str, Any]:
        self.start_driving_payload = payload
        return {
            "status": "active",
            "route_id": payload["route_id"],
            "remaining_distance_km": 184,
            "remaining_duration_minutes": 161,
            "eta": "14:35",
            "next_stop": {
                "id": "charging-1",
                "name": "ChargePoint Parndorf",
                "category": "charging",
            },
            "charging_required": True,
        }


def test_day7_realtime_instructions_require_truthful_voice_results() -> None:
    assert "never use a habitual opener before every tool result" in REALTIME_INSTRUCTIONS
    assert "After every failed tool result, give one clear, actionable spoken error" in REALTIME_INSTRUCTIONS
    assert "SCENIC is a route preference" in REALTIME_INSTRUCTIONS
    assert "never call a non-partner stop a partner" in REALTIME_INSTRUCTIONS
    assert "Mention a partner benefit only when that exact benefit is returned" in REALTIME_INSTRUCTIONS
    assert 'such as "Alright"' not in REALTIME_INSTRUCTIONS


def test_day7_tool_contract_preserves_start_driving_and_scenic_values() -> None:
    tool_by_name = {tool["name"]: tool for tool in REALTIME_TOOLS}
    driving = tool_by_name["start_driving"]
    route_priority = tool_by_name["plan_route"]["parameters"]["properties"]["priority"]

    assert driving["parameters"]["required"] == ["routeId", "confirmation"]
    assert tool_by_name["plan_route"]["parameters"]["required"] == [
        "destination",
        "priority",
    ]
    assert driving["parameters"]["properties"]["confirmation"]["enum"] == ["confirmed"]
    assert "SCENIC" in route_priority["enum"]
    assert "Never infer SCENIC" in route_priority["description"]


def test_day7_start_driving_preserves_current_route_id_and_returns_compact_facts() -> None:
    route_service = FakeRouteService()
    app = create_app(
        route_service=route_service,
        realtime_provider=FakeRealtimeProvider(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant/realtime/tools/start-driving",
            json={"routeId": "route-current", "confirmation": "confirmed"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "active",
        "sessionId": None,
        "routeId": "route-current",
        "remainingDistanceKm": 184,
        "remainingDurationMinutes": 161,
        "eta": "14:35",
        "nextStop": {
            "id": "charging-1",
            "name": "ChargePoint Parndorf",
            "category": "charging",
        },
        "chargingRequired": True,
    }
    assert route_service.start_driving_payload == {
        "route_id": "route-current",
        "confirmation": "confirmed",
    }


def test_day7_start_driving_contract_rejects_non_confirmed_requests() -> None:
    with pytest.raises(ValidationError):
        RealtimeToolStartDrivingRequest.model_validate(
            {"routeId": "route-current", "confirmation": "yes"}
        )

    request = RealtimeToolStartDrivingRequest.model_validate(
        {"routeId": "route-current", "confirmation": "confirmed"}
    )
    response = RealtimeToolStartDrivingResponse.model_validate(
        {
            "status": "active",
            "routeId": request.route_id,
            "remainingDistanceKm": 184,
            "remainingDurationMinutes": 161,
            "eta": "14:35",
            "chargingRequired": True,
        }
    )

    assert request.route_id == response.route_id
    assert response.model_dump(by_alias=True)["routeId"] == "route-current"


def test_day7_compact_partner_fact_rules_are_explicit_in_prompt() -> None:
    assert "Do not invent or estimate" in REALTIME_INSTRUCTIONS
    assert "provider details" in REALTIME_INSTRUCTIONS
    assert "raw provider payloads" not in REALTIME_INSTRUCTIONS
