import asyncio
from pathlib import Path

import pytest

from backend.app.core.errors import APIError
from backend.app.core.fixture_repository import FixtureRepository
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority, StopPinpoint
from backend.app.models.fixtures import Partner
from backend.app.services.trip.deterministic import (
    enrich_partner,
    select_route_stops,
    select_stop_amenities,
)
from backend.app.services.trip.ports import ProviderRoute
from backend.app.services.trip.service import RouteService


def stop(stop_id: str, coords: tuple[float, float], category: str = "attraction") -> StopPinpoint:
    return StopPinpoint(id=stop_id, name=stop_id, category=category, coords=coords, rating=4)


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


def test_route_attractions_exclude_origin_and_destination() -> None:
    geometry = ((16.37, 48.20), (17.50, 48.00), (19.04, 47.50))
    results = select_route_stops(
        [
            stop("origin", (16.45, 48.18)),
            stop("middle", (17.50, 48.00)),
            stop("destination", (18.95, 47.53)),
        ],
        geometry,
    )

    assert [item.id for item in results] == ["middle"]


def test_destination_search_does_not_apply_route_endpoint_exclusions() -> None:
    geometry = ((16.37, 48.20), (19.04, 47.50))
    results = select_route_stops(
        [stop("destination-attraction", (19.02, 47.51))],
        geometry,
        location="destination",
    )

    assert [item.id for item in results] == ["destination-attraction"]


def test_brand_network_enriches_a_provider_result_without_creating_a_location() -> None:
    provider_result = stop("place-chargepoint", (17.2, 47.6), "charging")
    network = Partner(
        id="network-chargepoint",
        kind="network",
        name="ChargePoint partner network",
        brand="ChargePoint",
        category="charging",
        provider_brands=("ChargePoint",),
        coords=None,
        benefit="ChargePoint partner access",
    )

    enriched = enrich_partner(
        provider_result.model_copy(update={"name": "ChargePoint Parndorf"}),
        [network],
    )

    assert enriched.coords == provider_result.coords
    assert enriched.partner is not None
    assert enriched.partner.id == "network-chargepoint"


def test_stop_amenities_use_500_m_radius_and_four_result_limit() -> None:
    center = (17.0, 47.0)
    results = select_stop_amenities(
        [
            stop("near-a", (17.002, 47.0), "coffee"),
            stop("near-b", (17.0, 47.003), "food"),
            stop("near-c", (16.997, 47.0), "rest"),
            stop("near-d", (17.0, 46.997), "service"),
            stop("near-e", (17.0035, 47.0), "coffee"),
            stop("far", (17.01, 47.0), "food"),
        ],
        center,
    )

    assert len(results) == 4
    assert "far" not in {item.id for item in results}
    assert {item.id for item in results} <= {"near-a", "near-b", "near-c", "near-d", "near-e"}


def test_stop_amenity_search_requires_a_selected_charging_stop() -> None:
    provider = type(
        "Provider",
        (),
        {
            "geocode": lambda self, place: asyncio.sleep(
                0, result=type(
                    "Place",
                    (),
                    {
                        "display_name": place,
                        "coordinates": Coordinates(lng=16.37, lat=48.20),
                    },
                )()
            ),
            "route": lambda self, origin, destination, priority, waypoints=(): asyncio.sleep(
                0, result=ProviderRoute(95_000, 3_600, ((16.37, 48.20), (19.04, 47.50)))
            ),
        },
    )()
    service = RouteService(provider, repository())
    asyncio.run(
        service.plan(AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST))
    )

    with pytest.raises(APIError) as error:
        asyncio.run(service.search_stop_amenities("missing", service.active_route_id or ""))

    assert error.value.code == "STALE_STOP"


def test_stop_amenity_search_rejects_stale_route_context() -> None:
    provider = type(
        "Provider",
        (),
        {
            "geocode": lambda self, place: asyncio.sleep(
                0,
                result=type(
                    "Place",
                    (),
                    {
                        "display_name": place,
                        "coordinates": Coordinates(lng=16.37, lat=48.20),
                    },
                )(),
            ),
            "route": lambda self, origin, destination, priority, waypoints=(): asyncio.sleep(
                0,
                result=ProviderRoute(95_000, 3_600, ((16.37, 48.20), (19.04, 47.50))),
            ),
        },
    )()
    service = RouteService(provider, repository())
    asyncio.run(
        service.plan(AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST))
    )

    with pytest.raises(APIError) as error:
        asyncio.run(service.search_stop_amenities("missing", "stale-route"))

    assert error.value.code == "STALE_ROUTE"
