import asyncio

import pytest

from backend.app.core.errors import APIError
from backend.app.integrations.openai.realtime import OpenAIRealtimeProvider


class FakeClientSecrets:
    def __init__(self) -> None:
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"value": "ek_test_secret"})()


class FakeRealtime:
    def __init__(self) -> None:
        self.client_secrets = FakeClientSecrets()


class FakeAsyncOpenAI:
    instance = None

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.realtime = FakeRealtime()
        FakeAsyncOpenAI.instance = self


def test_realtime_provider_configures_short_lived_mini_session(monkeypatch) -> None:
    monkeypatch.setattr("openai.AsyncOpenAI", FakeAsyncOpenAI)

    provider = OpenAIRealtimeProvider(
        "server-key",
        "gpt-realtime-2.1-mini",
        secret_seconds=600,
    )
    secret = asyncio.run(provider.create_client_secret())

    assert secret == "ek_test_secret"
    assert FakeAsyncOpenAI.instance is not None
    assert FakeAsyncOpenAI.instance.api_key == "server-key"
    kwargs = FakeAsyncOpenAI.instance.realtime.client_secrets.kwargs
    assert kwargs["expires_after"]["seconds"] == 600
    assert kwargs["session"]["type"] == "realtime"
    assert kwargs["session"]["model"] == "gpt-realtime-2.1-mini"
    assert kwargs["session"]["output_modalities"] == ["audio"]
    assert kwargs["session"]["audio"]["output"]["voice"] == "marin"
    tools = kwargs["session"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "plan_route",
        "search_route_poi",
        "reroute_through_poi",
        "search_stop_amenities",
    ]
    instructions = kwargs["session"]["instructions"]
    assert "Never ask permission before a mandatory charging stop is added" in instructions
    assert "at most two short sentences" in instructions
    assert "vehicleAlerts" not in instructions
    assert "Should I add a charging stop" not in instructions
    assert "Searching returns suggestions only and does not change the route" in instructions
    assert "search_stop_amenities" in instructions
    assert "500 metre stop radius" in instructions

    poi_tool = tools[1]
    assert poi_tool["parameters"]["required"] == ["category", "location"]
    assert poi_tool["parameters"]["properties"]["category"]["enum"] == [
        "hotel",
        "restaurant",
        "attraction",
        "charging",
        "coffee",
        "rest",
        "toilets",
        "fuel",
        "service",
    ]
    assert poi_tool["parameters"]["properties"]["location"]["enum"] == [
        "route",
        "stop",
        "destination",
    ]

    reroute_tool = tools[2]
    assert reroute_tool["parameters"]["required"] == [
        "poi_id",
        "route_id",
        "search_id",
        "confirmation",
    ]
    assert reroute_tool["parameters"]["properties"]["confirmation"]["enum"] == [
        "confirmed"
    ]

    amenities_tool = tools[3]
    assert amenities_tool["parameters"]["required"] == [
        "stopId",
        "routeId",
        "searchId",
    ]
    assert amenities_tool["parameters"]["properties"]["categories"]["items"]["enum"] == [
        "food",
        "coffee",
        "rest",
        "toilets",
        "shopping",
        "hotel",
        "restaurant",
        "service",
    ]


def test_realtime_provider_rejects_missing_server_key() -> None:
    provider = OpenAIRealtimeProvider(None, "gpt-realtime-2.1-mini")

    with pytest.raises(APIError) as error:
        asyncio.run(provider.create_client_secret())

    assert error.value.status_code == 503
    assert error.value.code == "REALTIME_UNAVAILABLE"
