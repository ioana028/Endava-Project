import asyncio
from pathlib import Path

import pytest

from backend.app.core.fixture_repository import FixtureRepository
from backend.app.core.errors import APIError
from backend.app.models.contracts import (
    AssistantIntent,
    Coordinates,
    RoutePriority,
    StopPinpoint,
)
from backend.app.services.trip.ports import (
    ChargingCandidate,
    GeocodedPlace,
    InvalidDestinationError,
    ProviderRoute,
    RoutingProviderError,
)
from backend.app.services.trip.deterministic import (
    estimate_eta_minutes,
    route_remaining_distance_km,
    select_chargers_iteratively,
)
from backend.app.services.trip.service import RouteService


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
        waypoints: tuple[GeocodedPlace, ...] | None = None,
    ) -> ProviderRoute:
        del origin, destination, priority, waypoints
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
        waypoints: tuple[GeocodedPlace, ...] | None = None,
    ) -> ProviderRoute:
        del origin, destination, priority, waypoints
        raise RoutingProviderError


class FakePlacesProvider:
    async def search(self, category, location, preference, route):
        del category, location, preference, route
        return [
            StopPinpoint(
                id="route-coffee",
                name="Route Coffee",
                category="coffee",
                coords=(17.5, 47.7),
            )
        ]


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
        waypoints: tuple[GeocodedPlace, ...] | None = None,
    ) -> ProviderRoute:
        del origin, destination, priority, waypoints
        return ProviderRoute(
            distance_meters=self.distance_meters,
            duration_seconds=self.duration_seconds,
            geometry=self.geometry,
        )


def repository() -> FixtureRepository:
    fixture_repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"), Path("data/partners/partners.json")
    )
    fixtures = fixture_repository.load()
    fixture_repository._fixtures = fixtures.model_copy(
        update={
            "telemetry": fixtures.telemetry.model_copy(
                update={"estimated_range_km": 120}
            )
        }
    )
    return fixture_repository


def intent(destination: str = "Budapest") -> AssistantIntent:
    return AssistantIntent(destination=destination, priority=RoutePriority.FASTEST)


def test_route_normalizes_provider_units_and_geometry() -> None:
    provider = FakeRoutingProvider(distance_meters=243_000)
    route = asyncio.run(RouteService(provider, repository()).plan(intent()))

    assert route.origin == "Vienna, Austria"
    assert route.destination == "Budapest"
    assert route.stats.total_distance_km == 243
    assert route.stats.driving_duration_minutes == 165
    assert route.stats.total_duration_minutes == 165
    assert route.charging_required is True
    assert route.charging_stop is None
    assert route.stops == []


def test_route_within_vehicle_range_has_no_range_warning() -> None:
    route = asyncio.run(
        RouteService(FakeRoutingProvider(distance_meters=95_000), repository()).plan(
            intent("Bratislava")
        )
    )

    assert route.alerts == []


def test_start_driving_returns_current_route_facts_without_replanning() -> None:
    provider = FakeRoutingProvider(distance_meters=95_000)
    route_service = RouteService(provider, repository())
    asyncio.run(route_service.plan(intent("Bratislava")))
    route_id = route_service.active_route_id

    facts = route_service.start_driving(route_id or "")

    assert facts["status"] == "active"
    assert facts["route_id"] == route_id
    assert len(provider.geocoded) == 2


def test_start_driving_rejects_stale_route_context() -> None:
    route_service = RouteService(FakeRoutingProvider(distance_meters=95_000), repository())
    asyncio.run(route_service.plan(intent("Bratislava")))

    with pytest.raises(APIError) as error:
        route_service.start_driving("stale-route")

    assert error.value.status_code == 409
    assert error.value.code == "STALE_ROUTE"


def test_route_beyond_vehicle_range_requires_charging_before_confirmation() -> None:
    route = asyncio.run(
        RouteService(FakeRoutingProvider(distance_meters=243_000), repository()).plan(
            intent()
        )
    )

    assert route.alerts == []
    assert route.charging_required is True
    assert route.charging_stop is None
    assert [(item.from_country, item.to_country) for item in route.border_crossings] == [
        ("Austria", "Hungary")
    ]
    assert [item.name for item in route.route_requirements] == [
        "Hungarian motorway vignette"
    ]


def test_search_route_poi_returns_generic_results_without_mutating_route() -> None:
    route_service = RouteService(FakeRoutingProvider(distance_meters=243_000), repository())
    asyncio.run(route_service.plan(intent()))

    results = asyncio.run(
        route_service.search_route_poi(
            category="restaurant",
            location="Budapest",
            preference="Italian",
        )
    )

    assert len(results) >= 1
    assert results[0].category == "restaurant"
    assert results[0].name == "Italia Ristorante"


def test_search_route_poi_rejects_missing_active_route() -> None:
    route_service = RouteService(FakeRoutingProvider(distance_meters=95_000), repository())

    with pytest.raises(APIError) as error:
        asyncio.run(route_service.search_route_poi(category="coffee", location="route"))

    assert error.value.code == "NO_ACTIVE_ROUTE"


def test_search_route_poi_returns_at_most_two_diverse_results() -> None:
    class ManyPlacesProvider:
        async def search(self, category, location, preference, route):
            del category, location, preference, route
            return [
                StopPinpoint(
                    id="near-a",
                    name="Near A",
                    category="attraction",
                    coords=(17.0, 48.035),
                    rating=5,
                ),
                StopPinpoint(
                    id="near-b",
                    name="Near B",
                    category="attraction",
                    coords=(17.01, 48.035),
                    rating=4.9,
                ),
                StopPinpoint(
                    id="farther",
                    name="Farther",
                    category="attraction",
                    coords=(18.0, 47.8),
                    rating=4,
                ),
            ]

    route_service = RouteService(
        FakeRoutingProvider(distance_meters=95_000),
        repository(),
        places_provider=ManyPlacesProvider(),
    )
    asyncio.run(route_service.plan(intent("Bratislava")))

    results = asyncio.run(route_service.search_route_poi("attraction", "route"))

    assert [result.id for result in results] == ["near-a", "farther"]


def test_route_poi_search_uses_active_route_context_for_charging() -> None:
    route_service = RouteService(FakeRoutingProvider(distance_meters=95_000), repository())
    asyncio.run(route_service.plan(intent("Budapest")))

    results = asyncio.run(
        route_service.search_route_poi(category="charging", location="route")
    )

    assert [result.name for result in results] == ["Ionity Győr"]
    assert results[0].coords == (17.5505239, 47.6768425)
    assert results[0].partner_benefit == "Ultra-Fast 350kW · 15% Partner Rate"


def test_reroute_through_poi_preserves_mandatory_charger() -> None:
    provider = FakeRoutingProvider(distance_meters=243_000)
    route_service = RouteService(
        provider, repository(), places_provider=FakePlacesProvider()
    )
    route = asyncio.run(route_service.plan(intent()))
    results = asyncio.run(route_service.search_route_poi("coffee", "route"))

    replacement = asyncio.run(
        route_service.reroute_through_poi(
            results[0].id,
            route_service._active_route_id,
            route_service._active_search_id,
        )
    )

    assert replacement.destination == route.destination
    assert [stop.id for stop in replacement.stops] == ["route-coffee"]
    assert len(provider.geocoded) == 2


def test_reroute_rejects_stale_poi_context() -> None:
    route_service = RouteService(
        FakeRoutingProvider(distance_meters=95_000),
        repository(),
        places_provider=FakePlacesProvider(),
    )
    asyncio.run(route_service.plan(intent("Bratislava")))
    results = asyncio.run(route_service.search_route_poi("coffee", "route"))

    with pytest.raises(APIError) as error:
        asyncio.run(
            route_service.reroute_through_poi(
                results[0].id,
                "old-route",
                route_service._active_search_id,
            )
        )

    assert error.value.code == "STALE_POI"


def test_return_to_main_route_preserves_route_and_clears_search_context() -> None:
    route_service = RouteService(FakeRoutingProvider(distance_meters=95_000), repository())
    asyncio.run(route_service.plan(intent("Bratislava")))
    route_id = route_service.active_route_id
    assert route_id is not None

    result = asyncio.run(route_service.return_to_main_route(route_id))

    assert result == {"status": "success", "route_id": route_id}
    assert route_service.active_route_id == route_id
    assert route_service.active_search_id is None


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


def test_long_route_selects_multiple_chargers_in_route_order() -> None:
    candidates = tuple(
        ChargingCandidate(
            stop=StopPinpoint(
                id=f"charger-{progress}",
                name=f"Charger {progress}",
                category="charging",
                coords=(16.37 + progress / 100, 48.20),
            ),
            distance_from_origin_km=progress,
        )
        for progress in (80, 160, 230)
    )

    selected = select_chargers_iteratively(
        candidates, route_distance_km=300, vehicle_range_km=100, safety_buffer_km=10
    )

    assert selected is not None
    assert [item.stop.id for item in selected] == ["charger-80", "charger-160", "charger-230"]


def test_charged_range_prevents_unnecessary_second_stop() -> None:
    candidates = tuple(
        ChargingCandidate(
            stop=StopPinpoint(
                id=f"charger-{progress}",
                name=f"Charger {progress}",
                category="charging",
                coords=(16.37 + progress / 100, 48.20),
            ),
            distance_from_origin_km=progress,
        )
        for progress in (80, 160)
    )

    selected = select_chargers_iteratively(
        candidates,
        route_distance_km=244,
        vehicle_range_km=95,
        safety_buffer_km=10,
        max_charged_range_km=250,
    )

    assert selected is not None
    assert [item.stop.id for item in selected] == ["charger-80"]


def test_route_progress_helpers_report_remaining_distance_and_eta() -> None:
    assert route_remaining_distance_km(300, 160) == 140
    assert estimate_eta_minutes(140, 70) == 120


def test_route_exposes_driving_facts_and_next_mandatory_stop() -> None:
    route_service = RouteService(FakeRoutingProvider(distance_meters=243_000), repository())
    asyncio.run(route_service.plan(intent()))

    facts = route_service.route_state_facts()

    assert facts["status"] == "active"
    assert facts["route_id"] == route_service.active_route_id
    assert facts["remaining_distance_km"] == 243
    assert facts["remaining_duration_minutes"] == 165
    assert facts["next_stop"] is None
    assert facts["charging_required"] is True

