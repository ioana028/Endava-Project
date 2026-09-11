import asyncio
from pathlib import Path

import pytest

from backend.app.core.fixture_repository import FixtureRepository
from backend.app.core.errors import APIError
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority
from backend.app.services.trip.ports import (
    GeocodedPlace,
    InvalidDestinationError,
    ProviderRoute,
    RoutingProviderError,
)
from backend.app.services.trip.service import RouteService
from backend.app.services.assistant.service import AssistantService, LocalTextAIModule


class FakeRoutingProvider:
    def __init__(self, distance_meters: float = 243_000) -> None:
        self.distance_meters = distance_meters
        self.geocoded: list[str] = []

    async def geocode(self, place: str) -> GeocodedPlace:
        self.geocoded.append(place)
        if place == "Unknown Place":
            raise InvalidDestinationError
        return GeocodedPlace(
            display_name=place,
            coordinates=Coordinates(lng=16.37, lat=48.20),
        )

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
    ) -> ProviderRoute:
        del origin, destination, priority
        return ProviderRoute(
            distance_meters=self.distance_meters,
            duration_seconds=9_900,
            geometry=((16.37, 48.20), (19.04, 47.50)),
        )


class FailingRoutingProvider(FakeRoutingProvider):
    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
    ) -> ProviderRoute:
        del origin, destination, priority
        raise RoutingProviderError


class InvalidRoutingProvider(FakeRoutingProvider):
    def __init__(self, distance_meters: float, duration_seconds: float, geometry: tuple[tuple[float, float], ...]) -> None:
        super().__init__(distance_meters)
        self.duration_seconds = duration_seconds
        self.geometry = geometry

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
    ) -> ProviderRoute:
        del origin, destination, priority
        return ProviderRoute(
            distance_meters=self.distance_meters,
            duration_seconds=self.duration_seconds,
            geometry=self.geometry,
        )


def repository() -> FixtureRepository:
    fixture_repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"), Path("data/partners/partners.json")
    )
    fixture_repository.load()
    return fixture_repository


def intent(destination: str = "Budapest") -> AssistantIntent:
    return AssistantIntent(destination=destination, priority=RoutePriority.FASTEST)


def test_route_normalizes_provider_units_and_geometry() -> None:
    provider = FakeRoutingProvider(distance_meters=243_000)
    route = asyncio.run(RouteService(provider, repository()).plan(intent()))

    assert route.origin == "Vienna, Austria"
    assert route.destination == "Budapest"
    assert route.stats.total_distance_km == 243
    assert route.stats.total_duration_minutes == 165
    assert route.geometry == [(16.37, 48.2), (19.04, 47.5)]
    assert route.stops == []


def test_route_within_vehicle_range_has_no_range_warning() -> None:
    route = asyncio.run(
        RouteService(FakeRoutingProvider(distance_meters=95_000), repository()).plan(
            intent("Bratislava")
        )
    )

    assert route.alerts == []


def test_route_beyond_vehicle_range_returns_charging_question() -> None:
    route = asyncio.run(
        RouteService(FakeRoutingProvider(distance_meters=243_000), repository()).plan(
            intent()
        )
    )

    assert len(route.alerts) == 1
    assert route.alerts[0].type == "VEHICLE"
    assert route.alerts[0].severity == "WARNING"
    assert "estimated range is 95 km" in route.alerts[0].message
    assert "route distance is 243 km" in route.alerts[0].message
    assert route.stops == []


def test_invalid_destination_returns_stable_api_error() -> None:
    with pytest.raises(APIError) as error:
        asyncio.run(
            RouteService(FakeRoutingProvider(), repository()).plan(
                intent("Unknown Place")
            )
        )

    assert error.value.status_code == 400
    assert error.value.code == "INVALID_DESTINATION"


def test_provider_failure_returns_stable_api_error() -> None:
    with pytest.raises(APIError) as error:
        asyncio.run(
            RouteService(FailingRoutingProvider(), repository()).plan(intent())
        )

    assert error.value.status_code == 503
    assert error.value.code == "ROUTING_UNAVAILABLE"


@pytest.mark.parametrize(
    ("distance_meters", "duration_seconds", "geometry"),
    [
        (-1, 9_900, ((16.37, 48.20), (19.04, 47.50))),
        (243_000, -1, ((16.37, 48.20), (19.04, 47.50))),
        (243_000, 9_900, ((16.37, 48.20),)),
    ],
)
def test_invalid_provider_route_returns_stable_api_error(
    distance_meters: float,
    duration_seconds: float,
    geometry: tuple[tuple[float, float], ...],
) -> None:
    provider = InvalidRoutingProvider(distance_meters, duration_seconds, geometry)

    with pytest.raises(APIError) as error:
        asyncio.run(RouteService(provider, repository()).plan(intent()))

    assert error.value.status_code == 503
    assert error.value.code == "INVALID_ROUTE"


def test_assistant_service_returns_route_from_extracted_intent() -> None:
    route_service = RouteService(FakeRoutingProvider(), repository())
    service = AssistantService(LocalTextAIModule(), route_service)

    response = asyncio.run(
        service.interact("Suzanne, take me to Budapest fast", "day2-test")
    )

    assert response.intent.destination == "Budapest"
    assert response.route is not None
    assert response.route.stats.total_distance_km == 243
    assert response.route.alerts[0].type == "VEHICLE"
    response_json = response.model_dump(by_alias=True)
    assert response_json["spokenResponse"]
    assert response_json["route"]["stats"]["totalDistanceKm"] == 243
    assert response_json["route"]["stats"]["totalDurationMinutes"] == 165