import asyncio

import httpx
import pytest

from backend.app.integrations.google_maps.routing import GoogleMapsRoutingProvider
from backend.app.integrations.places.google import GooglePlacesProvider
from backend.app.models.contracts import Coordinates, RoutePriority
from backend.app.services.trip.ports import GeocodedPlace, JourneyProviderError, ProviderRoute, RoutingProviderError


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class FakePlacesClient:
    responses: list[FakeResponse] = []
    calls: list[dict[str, object]] = []

    def __init__(self, **kwargs: object) -> None:
        self.timeout = kwargs["timeout"]

    async def __aenter__(self) -> "FakePlacesClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


class FakeRoutingClient:
    response: FakeResponse | Exception

    def __init__(self, **kwargs: object) -> None:
        del kwargs

    async def __aenter__(self) -> "FakeRoutingClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        del url, kwargs
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def route() -> ProviderRoute:
    return ProviderRoute(
        distance_meters=300_000,
        duration_seconds=10_000,
        geometry=((16.0, 48.0), (16.1, 48.0), (18.0, 48.0), (19.0, 47.5)),
    )


def place(place_id: str = "places/fuel") -> dict[str, object]:
    return {
        "id": place_id,
        "displayName": {"text": "Fuel Stop"},
        "location": {"longitude": 16.05, "latitude": 48.001},
        "types": ["gas_station", "convenience_store", "cafe"],
        "rating": 4.2,
        "formattedAddress": "Route 1",
    }


def test_places_samples_by_distance_and_deduplicates_provider_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    FakePlacesClient.calls = []
    FakePlacesClient.responses = [
        FakeResponse({"places": [place()]}),
        FakeResponse({"places": [place(), place("places/second")]}),
        FakeResponse({"places": []}),
    ]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    provider = GooglePlacesProvider(
        "test-key", sample_interval_km=100, max_search_points=3
    )
    results = asyncio.run(provider.search("fuel", route=route()))

    assert len(FakePlacesClient.calls) == 3
    assert len(results) == 2
    assert results[0].category == "fuel"
    assert "fuel station" in results[0].tag
    assert "cafe" in results[0].tag
    assert FakePlacesClient.calls[0]["headers"]["X-Goog-FieldMask"].startswith("places.id")


def test_places_timeout_is_translated_to_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class TimeoutClient(FakePlacesClient):
        async def post(self, url: str, **kwargs: object) -> FakeResponse:
            del url, kwargs
            raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", TimeoutClient
    )

    with pytest.raises(JourneyProviderError, match="Google Places search failed"):
        asyncio.run(GooglePlacesProvider("test-key").search("attraction", route=route()))


def test_places_malformed_json_is_translated_to_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakePlacesClient.responses = [FakeResponse([])]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    with pytest.raises(JourneyProviderError, match="Google Places search failed"):
        asyncio.run(GooglePlacesProvider("test-key").search("attraction", route=route()))


def test_unconfigured_places_provider_is_rejected_before_network_call() -> None:
    with pytest.raises(JourneyProviderError, match="not configured"):
        asyncio.run(GooglePlacesProvider("").search("fuel", route=route()))


def test_routing_malformed_response_is_translated_to_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRoutingClient.response = FakeResponse({"routes": []})
    monkeypatch.setattr(
        "backend.app.integrations.google_maps.routing.httpx.AsyncClient",
        FakeRoutingClient,
    )
    provider = GoogleMapsRoutingProvider("test-key")
    origin = GeocodedPlace("Origin", Coordinates(lng=16, lat=48))
    destination = GeocodedPlace("Destination", Coordinates(lng=19, lat=47))

    with pytest.raises(RoutingProviderError, match="response was invalid"):
        asyncio.run(
            provider.route(origin, destination, RoutePriority.FASTEST)
        )
