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
    assert kwargs["session"]["tools"][0]["name"] == "plan_route"
    assert "vehicleAlerts" in kwargs["session"]["instructions"]
    assert "Never stop after saying only" in kwargs["session"]["instructions"]


def test_realtime_provider_rejects_missing_server_key() -> None:
    provider = OpenAIRealtimeProvider(None, "gpt-realtime-2.1-mini")

    with pytest.raises(APIError) as error:
        asyncio.run(provider.create_client_secret())

    assert error.value.status_code == 503
    assert error.value.code == "REALTIME_UNAVAILABLE"
