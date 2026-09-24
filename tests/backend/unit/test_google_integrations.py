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
    calls: list[dict[str, object]] = []

    def __init__(self, **kwargs: object) -> None:
        del kwargs

    async def __aenter__(self) -> "FakeRoutingClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
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


def test_repeated_places_search_is_coalesced(monkeypatch: pytest.MonkeyPatch) -> None:
    FakePlacesClient.calls = []
    FakePlacesClient.responses = [FakeResponse({"places": [place()]})]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    provider = GooglePlacesProvider("test-key", max_search_points=2)
    first = asyncio.run(provider.search("coffee", location="stop", route=route(), near_coords=(16.05, 48.001)))
    second = asyncio.run(provider.search("coffee", location="stop", route=route(), near_coords=(16.05, 48.001)))

    assert [item.id for item in first] == [item.id for item in second]
    assert len(FakePlacesClient.calls) == 1


def test_repeated_route_request_is_coalesced(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeRoutingClient.calls = []
    FakeRoutingClient.response = FakeResponse({
        "routes": [{
            "distanceMeters": 1000,
            "duration": "60s",
            "polyline": {"geoJsonLinestring": {"coordinates": [[16.0, 48.0], [16.1, 48.0]]}},
            "travelAdvisory": {"tollInfo": {}},
        }]
    })
    monkeypatch.setattr(
        "backend.app.integrations.google_maps.routing.httpx.AsyncClient", FakeRoutingClient
    )

    provider = GoogleMapsRoutingProvider("test-key")
    origin = GeocodedPlace("Vienna", Coordinates(lng=16.0, lat=48.0))
    destination = GeocodedPlace("Budapest", Coordinates(lng=19.0, lat=47.5))
    first = asyncio.run(provider.route(origin, destination, RoutePriority.FASTEST))
    second = asyncio.run(provider.route(origin, destination, RoutePriority.FASTEST))

    assert first == second
    assert len(FakeRoutingClient.calls) == 1


def test_places_stop_search_uses_stop_center_and_structured_amenities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakePlacesClient.calls = []
    FakePlacesClient.responses = [FakeResponse({"places": [place()]})]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    results = asyncio.run(
        GooglePlacesProvider("test-key").search(
            "coffee", location="stop", route=route(), near_coords=(16.05, 48.001)
        )
    )

    assert len(FakePlacesClient.calls) == 1
    request = FakePlacesClient.calls[0]["json"]
    center = request["locationBias"]["circle"]["center"]
    assert center == {"latitude": 48.001, "longitude": 16.05}
    assert results[0].amenities == ("fuel station", "cafe", "convenience store")


def test_places_stop_search_keeps_nearby_result_off_the_route_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakePlacesClient.calls = []
    nearby_place = place("places/nearby-restaurant")
    nearby_place["location"] = {"longitude": 18.0, "latitude": 47.5}
    FakePlacesClient.responses = [FakeResponse({"places": [nearby_place]})]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    results = asyncio.run(
        GooglePlacesProvider("test-key", nearby_search_radius_meters=500).search(
            "restaurant",
            location="stop",
            route=route(),
            near_coords=(18.0, 47.5),
        )
    )

    assert [result.id for result in results] == ["places/nearby-restaurant"]


def test_charging_search_keeps_google_chargers_for_later_route_legs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakePlacesClient.calls = []
    later_charger = place("places/later-charger")
    later_charger["displayName"] = {"text": "Later Google Charger"}
    later_charger["location"] = {"longitude": 19.0, "latitude": 47.5}
    later_charger["types"] = ["electric_vehicle_charging_station"]
    FakePlacesClient.responses = [
        FakeResponse({"places": [later_charger]}),
        FakeResponse({"places": [later_charger]}),
    ]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    candidates = asyncio.run(
        GooglePlacesProvider("test-key", max_search_points=2).search_charging(
            route(), max_distance_km=10
        )
    )

    assert candidates == ()


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


def test_google_places_uses_configured_route_and_nearby_radii(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakePlacesClient.calls = []
    FakePlacesClient.responses = [FakeResponse({"places": [place()]})]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient", FakePlacesClient
    )

    provider = GooglePlacesProvider(
        "test-key",
        search_radius_meters=7_500,
        nearby_search_radius_meters=500,
        max_search_points=2,
    )

    asyncio.run(
        provider.search(
            "coffee",
            location="stop",
            route=route(),
            near_coords=(16.05, 48.001),
        )
    )

    request = FakePlacesClient.calls[0]["json"]
    assert request["locationBias"]["circle"]["radius"] == 500

    FakePlacesClient.calls = []
    FakePlacesClient.responses = [
        FakeResponse({"places": [place()]}),
        FakeResponse({"places": [place()]}),
        FakeResponse({"places": [place()]}),
        FakeResponse({"places": [place()]}),
    ]
    asyncio.run(provider.search("attraction", location="route", route=route()))
    request = FakePlacesClient.calls[0]["json"]
    assert "searchAlongRouteParameters" in request
    assert request["searchAlongRouteParameters"]["polyline"]["encodedPolyline"]


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


def test_scenic_routing_avoids_highways_except_known_scenic_corridors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeRoutingClient.calls = []
    FakeRoutingClient.response = FakeResponse({
        "routes": [{
            "distanceMeters": 300_000,
            "duration": "10000s",
            "polyline": {"geoJsonLinestring": {"coordinates": [[16, 48], [19, 47.5]]}},
        }],
    })
    monkeypatch.setattr(
        "backend.app.integrations.google_maps.routing.httpx.AsyncClient",
        FakeRoutingClient,
    )
    provider = GoogleMapsRoutingProvider("test-key")
    origin = GeocodedPlace("Vienna", Coordinates(lng=16, lat=48))

    asyncio.run(
        provider.route(
            origin,
            GeocodedPlace("Budapest, Hungary", Coordinates(lng=19, lat=47)),
            RoutePriority.SCENIC,
        )
    )
    assert FakeRoutingClient.calls[-1]["json"]["routeModifiers"] == {
        "avoidHighways": True
    }

    asyncio.run(
        provider.route(
            origin,
            GeocodedPlace("Grossglockner Alpine Road", Coordinates(lng=12, lat=47)),
            RoutePriority.SCENIC,
        )
    )
    assert "routeModifiers" not in FakeRoutingClient.calls[-1]["json"]
