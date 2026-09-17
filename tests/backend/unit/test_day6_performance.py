import asyncio
import logging

import pytest

from backend.app.integrations.google_maps.routing import GoogleMapsRoutingProvider
from backend.app.integrations.places.google import GooglePlacesProvider
from backend.app.models.contracts import Coordinates, RoutePriority
from backend.app.services.trip.ports import GeocodedPlace, ProviderRoute


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class FakePlacesClient:
    responses: list[FakeResponse] = []

    def __init__(self, **kwargs: object) -> None:
        self.timeout = kwargs["timeout"]

    async def __aenter__(self) -> "FakePlacesClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        del url, kwargs
        if not self.responses:
            return FakeResponse({"places": []})
        return self.responses.pop(0)


class FakeRoutingClient:
    geocode_response: FakeResponse | None = None
    route_response: FakeResponse | None = None

    def __init__(self, **kwargs: object) -> None:
        del kwargs

    async def __aenter__(self) -> "FakeRoutingClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, **kwargs: object) -> FakeResponse:
        del url, kwargs
        if self.geocode_response is None:
            raise AssertionError("geocode response was not configured")
        return self.geocode_response

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        del url, kwargs
        if self.route_response is None:
            raise AssertionError("route response was not configured")
        return self.route_response


@pytest.mark.parametrize("provider_name", ["geocode_ms", "route_provider_ms"])
def test_google_routing_emits_runtime_spans_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    provider_name: str,
) -> None:
    FakeRoutingClient.geocode_response = FakeResponse(
        {
            "results": [
                {
                    "formatted_address": "Budapest, Hungary",
                    "geometry": {"location": {"lng": 19.04, "lat": 47.5}},
                }
            ]
        }
    )
    FakeRoutingClient.route_response = FakeResponse(
        {
            "routes": [
                {
                    "distanceMeters": "12300",
                    "duration": "1230s",
                    "polyline": {
                        "geoJsonLinestring": {
                            "coordinates": [
                                [16.37, 48.2],
                                [19.04, 47.5],
                            ]
                        }
                    },
                    "travelAdvisory": {"tollInfo": {"estimatedPrice": []}},
                }
            ]
        }
    )
    monkeypatch.setattr(
        "backend.app.integrations.google_maps.routing.httpx.AsyncClient",
        FakeRoutingClient,
    )

    provider = GoogleMapsRoutingProvider("super-secret-key")
    with caplog.at_level(logging.INFO):
        asyncio.run(provider.geocode("Budapest"))
        asyncio.run(
            provider.route(
                GeocodedPlace("Origin", Coordinates(lng=16.37, lat=48.2)),
                GeocodedPlace("Destination", Coordinates(lng=19.04, lat=47.5)),
                RoutePriority.FASTEST,
            )
        )

    assert provider_name in caplog.text
    assert "super-secret-key" not in caplog.text


def test_google_places_emits_charging_lookup_timing_without_raw_payloads(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    FakePlacesClient.responses = [
        FakeResponse(
            {
                "places": [
                    {
                        "id": "place-1",
                        "displayName": {"text": "ChargePoint"},
                        "location": {"longitude": 16.05, "latitude": 48.001},
                        "types": ["electric_vehicle_charging_station"],
                        "rating": 4.7,
                        "formattedAddress": "Route 1",
                        "evChargeOptions": {"connectorAggregation": [{"maxChargeRateKw": 150}]},
                    }
                ]
            }
        )
    ]
    monkeypatch.setattr(
        "backend.app.integrations.places.google.httpx.AsyncClient",
        FakePlacesClient,
    )

    route = ProviderRoute(
        distance_meters=25_000,
        duration_seconds=1_800,
        geometry=((16.0, 48.0), (16.1, 48.0), (16.2, 48.0)),
    )
    provider = GooglePlacesProvider("test-key")
    with caplog.at_level(logging.INFO):
        asyncio.run(provider.search("charging", location="route", route=route))
        asyncio.run(provider.search_charging(route, 120))

    assert "charging_lookup_ms" in caplog.text
    assert "maxChargeRateKw" not in caplog.text
    assert "super-secret-key" not in caplog.text
