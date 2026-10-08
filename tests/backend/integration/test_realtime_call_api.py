from fastapi.testclient import TestClient
import pytest

from backend.app.main import create_app
from backend.app.models.contracts import RouteRequirement
from backend.app.services.commerce.service import CommerceService
from backend.app.services.wallet.service import WalletService


class Provider:
    calls = 0
    closed = False

    async def create_call(self, sdp):
        self.calls += 1
        self.offer = sdp
        return "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"

    async def aclose(self):
        self.closed = True


class RouteContext:
    active_route_id = "route1"
    active_route_requirements = (RouteRequirement(id="hungarian-motorway-vignette", name="Hungarian motorway vignette", country="HU", kind="vignette"),)

    def __init__(self):
        self.purchased = []

    @property
    def route_session_facts(self):
        return {"route_id": self.active_route_id, "session_generation": 1,
                "purchased_vignette_requirement_ids": self.purchased,
                "remaining_requirements": [r for r in self.active_route_requirements if r.id not in self.purchased]}

    def mark_vignette_purchased(self, requirement_id):
        if requirement_id not in self.purchased:
            self.purchased.append(requirement_id)


def test_unified_endpoint_returns_only_sdp_and_closes_provider():
    provider = Provider()
    app = create_app(route_service=RouteContext(), realtime_provider=provider)
    offer = "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\n"
    with TestClient(app) as client:
        response = client.post("/api/assistant/realtime/call", content=offer, headers={"Content-Type": "application/sdp"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/sdp"
    assert response.headers["cache-control"] == "no-store"
    assert provider.offer == offer and provider.calls == 1
    assert provider.closed
    assert "secret" not in response.text


@pytest.mark.parametrize("content,content_type,status", [
    ("bad", "application/sdp", 422),
    (b"\xff", "application/sdp", 422),
    ("v=0", "application/json", 415),
    ("v=0" + "x" * 65_536, "application/sdp", 413),
], ids=["malformed", "invalid-utf8", "wrong-content-type", "oversize"])
def test_invalid_offer_never_calls_openai(content, content_type, status):
    provider = Provider()
    with TestClient(create_app(route_service=RouteContext(), realtime_provider=provider)) as client:
        response = client.post("/api/assistant/realtime/call", content=content, headers={"Content-Type": content_type})
    assert response.status_code == status
    assert provider.calls == 0


def test_purchase_resolves_id_and_returns_updated_facts_then_remains_idempotent():
    route = RouteContext()
    app = create_app(route_service=route, realtime_provider=Provider())
    app.state.commerce_service = CommerceService(route, WalletService())
    payload = {"routeId": "route1", "confirmation": "confirmed"}
    with TestClient(app) as client:
        first = client.post("/api/assistant/realtime/tools/purchase-vignette", json=payload)
        duplicate = client.post("/api/assistant/realtime/tools/purchase-vignette", json=payload)
    assert first.status_code == duplicate.status_code == 200
    assert first.json()["requirementId"] == "hungarian-motorway-vignette"
    assert first.json()["sessionFacts"]["remainingRequirements"] == []
    assert first.json()["sessionFacts"]["purchasedVignetteRequirementIds"] == ["hungarian-motorway-vignette"]
    assert duplicate.json()["status"] == "duplicate"
    assert first.json()["transactionId"] == duplicate.json()["transactionId"]
