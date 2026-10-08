import asyncio
import json

import httpx
import pytest

from backend.app.core.errors import APIError
from backend.app.integrations.openai.realtime import OpenAIRealtimeProvider

OFFER = "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\n"
ANSWER = "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"


def test_unified_call_sends_sdp_and_authoritative_session_without_secret_round_trip():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url == "https://api.openai.com/v1/realtime/calls"
        assert request.headers["authorization"] == "Bearer server-key"
        body = request.content.decode()
        assert 'name="sdp"' in body and OFFER in body
        session_start = body.index('{"type": "realtime"')
        session = json.JSONDecoder().raw_decode(body[session_start:])[0]
        assert session["model"] == "configured-model"
        assert session["audio"]["input"]["turn_detection"]["create_response"] is False
        assert session["audio"]["output"]["voice"] == "marin"
        assert len(session["tools"]) == 11
        return httpx.Response(201, text=ANSWER)

    async def run():
        provider = OpenAIRealtimeProvider("server-key", "configured-model")
        provider._http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = provider._http_client
        assert await provider.create_call(OFFER) == ANSWER
        assert await provider.create_call(OFFER) == ANSWER
        assert provider._http_client is client
        await provider.aclose()
        assert client.is_closed

    asyncio.run(run())
    assert len(calls) == 2


@pytest.mark.parametrize("status,body", [(401, "private upstream detail"), (429, "rate limit"), (200, "not an SDP")])
def test_upstream_failure_is_safe_and_not_retried(status, body, caplog):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=body)

    async def run():
        provider = OpenAIRealtimeProvider("sensitive-server-key", "model")
        provider._http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            with pytest.raises(APIError) as error:
                await provider.create_call(OFFER)
            assert error.value.code == "REALTIME_UNAVAILABLE"
            assert body not in error.value.message
        finally:
            await provider.aclose()

    asyncio.run(run())
    assert len(calls) == 1
    assert "sensitive-server-key" not in caplog.text
    assert "private upstream detail" not in caplog.text


def test_unified_call_requires_server_configuration():
    with pytest.raises(APIError) as error:
        asyncio.run(OpenAIRealtimeProvider(None, "model").create_call(OFFER))
    assert error.value.code == "REALTIME_UNAVAILABLE"
