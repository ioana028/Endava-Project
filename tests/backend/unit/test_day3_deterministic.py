import asyncio
from pathlib import Path

import pytest

from backend.app.core.errors import APIError
from backend.app.core.fixture_repository import FixtureRepository
from backend.app.models.contracts import StopPinpoint
from backend.app.models.fixtures import Partner
from backend.app.services.recommendation.poi import POIService
from backend.app.services.trip.country_rules import (
    derive_requirements,
    detect_border_crossings,
)
from backend.app.services.trip.deterministic import enrich_partner, rank_pois, select_charger
from backend.app.services.trip.ports import (
    ChargingCandidate,
    GeocodedPlace,
    POICandidate,
    ProviderRoute,
)
from backend.app.services.trip.service import RouteService
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority
from backend.app.integrations.places.google import GooglePlacesProvider


def stop(stop_id: str, category: str = "charging", detour: float = 1) -> StopPinpoint:
    return StopPinpoint(
        id=stop_id,
        name=stop_id,
        category=category,
        coords=(17.0, 47.0),
        detour_minutes=detour,
    )


def test_charger_selection_filters_unsafe_candidates_before_ranking() -> None:
    selected = select_charger(
        [
            ChargingCandidate(stop("incompatible"), compatible=False),
            ChargingCandidate(stop("unavailable"), available=False),
            ChargingCandidate(stop("far"), distance_from_route_km=4),
            ChargingCandidate(stop("near"), distance_from_route_km=1),
        ]
    )

    assert selected is not None
    assert selected.stop.id == "near"


def test_partner_enrichment_does_not_create_vignette_benefit() -> None:
    vignette = Partner(
        id="vignette",
        name="Hungarian vignette",
        category="vignette",
        coords=(17, 47),
        tag="Automated Toll Clearing",
        detour_minutes=0,
    )

    enriched = enrich_partner(stop("vignette", "vignette"), [vignette])

    assert enriched.partner is not None
    assert enriched.partner.benefit is None


def test_country_rules_detect_borders_and_requirements() -> None:
    crossings = detect_border_crossings(["AT", "HU"])
    requirements = derive_requirements(["AT", "HU"])

    assert crossings[0].from_country == "Austria"
    assert crossings[0].to_country == "Hungary"
    assert {requirement.id for requirement in requirements} == {
        "at-motorway-vignette",
        "hu-motorway-vignette",
    }


class FakePOIProvider:
    def __init__(self, candidates: tuple[POICandidate, ...]) -> None:
        self.candidates = candidates

    async def search_pois(self, route, category, preference):
        del route, category, preference
        return self.candidates


def test_poi_search_ranks_without_mutating_route() -> None:
    route = ProviderRoute(1000, 60, ((17, 47), (18, 48)))
    service = POIService(
        FakePOIProvider(
            (
                POICandidate(stop("restaurant-b", "restaurant", 3), 0.8, 4),
                POICandidate(stop("restaurant-a", "restaurant", 1), 0.8, 4),
            )
        )
    )

    result = asyncio.run(service.search(route, "restaurant"))

    assert [item.id for item in result] == ["restaurant-a", "restaurant-b"]
    assert route.geometry == ((17, 47), (18, 48))


def repository() -> FixtureRepository:
    fixture_repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"), Path("data/partners/partners.json")
    )
    fixture_repository.load()
    return fixture_repository


class WaypointRoutingProvider:
    def __init__(self) -> None:
        self.waypoints: list[tuple[GeocodedPlace, ...]] = []

    async def geocode(self, place: str) -> GeocodedPlace:
        return GeocodedPlace(place, Coordinates(lng=16, lat=48))

    async def route(self, origin, destination, priority, waypoints=()):
        del origin, destination, priority
        self.waypoints.append(waypoints)
        if waypoints:
            return ProviderRoute(251_000, 10_200, ((16, 48), (17, 47), (19, 47)))
        return ProviderRoute(243_000, 9_900, ((16, 48), (19, 47)))

    async def route_with_countries(self, origin, destination, priority, waypoints=()):
        del origin, destination, priority
        self.waypoints.append(waypoints)
        if waypoints:
            distance_meters = 251_000
            duration_seconds = 10_200
            geometry = ((16, 48), (17, 47), (19, 47))
        else:
            distance_meters = 243_000
            duration_seconds = 9_900
            geometry = ((16, 48), (19, 47))
        return ProviderRoute(
            distance_meters,
            duration_seconds,
            geometry,
            countries=("AT", "HU"),
        )


class FakeChargingProvider:
    async def search_charging(self, route, max_distance_km):
        del route
        return (
            ChargingCandidate(
                stop("too-far"), distance_from_route_km=max_distance_km + 1
            ),
            ChargingCandidate(
                stop("ionity-gyor"), distance_from_route_km=max_distance_km
            ),
        )


def test_route_service_automatically_reroutes_through_safe_charger() -> None:
    provider = WaypointRoutingProvider()
    route = asyncio.run(
        RouteService(
            provider,
            repository(),
            charging_provider=FakeChargingProvider(),
        ).plan(AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST))
    )

    assert route.stops[0].id == "ionity-gyor"
    assert route.stops[0].mandatory is True
    assert route.stats.driving_duration_minutes == 170
    assert route.stats.total_duration_minutes == 171
    assert len(provider.waypoints) == 2
    assert provider.waypoints[1][0].display_name == "ionity-gyor"


def test_route_service_derives_route_facts_from_provider_metadata() -> None:
    provider = WaypointRoutingProvider()
    provider.route = provider.route_with_countries
    route = asyncio.run(
        RouteService(provider, repository()).plan(
            AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST)
        )
    )

    assert [(item.from_country, item.to_country) for item in route.border_crossings] == [
        ("Austria", "Hungary")
    ]
    assert [item.id for item in route.route_requirements] == [
        "at-motorway-vignette",
        "hu-motorway-vignette",
    ]


class EmptyChargingProvider:
    async def search_charging(self, route, max_distance_km):
        del route, max_distance_km
        return ()


def test_route_service_reports_no_suitable_charger() -> None:
    with pytest.raises(APIError) as error:
        asyncio.run(
            RouteService(
                WaypointRoutingProvider(),
                repository(),
                charging_provider=EmptyChargingProvider(),
            ).plan(AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST))
        )

    assert error.value.code == "NO_SUITABLE_CHARGER"


def test_poi_route_through_calls_waypoint_routing_explicitly() -> None:
    provider = WaypointRoutingProvider()
    route = ProviderRoute(1000, 60, ((17, 47), (18, 48)))
    service = POIService(FakePOIProvider(()), provider)
    origin = GeocodedPlace("Vienna", Coordinates(lng=16, lat=48))
    destination = GeocodedPlace("Budapest", Coordinates(lng=19, lat=47))

    result = asyncio.run(
        service.route_through(
            route,
            origin,
            destination,
            RoutePriority.FASTEST,
            stop("hotel", "hotel"),
        )
    )

    assert result.distance_meters == 251_000
    assert provider.waypoints[0][0].display_name == "hotel"


def test_google_places_provider_maps_and_filters_route_results() -> None:
    provider = GooglePlacesProvider("test-key")
    route = ProviderRoute(1000, 60, ((17.0, 47.0), (18.0, 47.0)))

    result = provider._to_stop(
        {
            "id": "places/cool-place",
            "displayName": {"text": "Cool Place"},
            "location": {"longitude": 17.5, "latitude": 47.005},
            "rating": 4.7,
            "editorialSummary": {"text": "A memorable stop"},
        },
        "attraction",
        route,
    )

    assert result is not None
    assert result.name == "Cool Place"
    assert result.category == "attraction"
    assert result.rating == 4.7
    assert result.tag == "A memorable stop"
    assert provider._to_stop(
        {
            "id": "places/far-away",
            "displayName": {"text": "Far Away"},
            "location": {"longitude": 17.5, "latitude": 47.1},
        },
        "attraction",
        route,
    ) is None