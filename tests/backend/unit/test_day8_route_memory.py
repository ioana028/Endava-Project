import asyncio
from pathlib import Path

from backend.app.core.fixture_repository import FixtureRepository
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority, RouteRequirement
from backend.app.services.commerce.service import CommerceService
from backend.app.services.trip.ports import GeocodedPlace, ProviderRoute
from backend.app.services.trip.service import RouteService
from backend.app.services.wallet.service import WalletService


class RouteProvider:
    async def geocode(self, place: str) -> GeocodedPlace:
        return GeocodedPlace(place, Coordinates(lng=16.37, lat=48.20))

    async def route(self, origin, destination, priority, waypoints=()):
        del origin, destination, priority, waypoints
        return ProviderRoute(95_000, 3_600, ((16.37, 48.20), (19.04, 47.50)))


def repository() -> FixtureRepository:
    repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"), Path("data/partners/partners.json")
    )
    repository.load()
    return repository


def test_route_session_resets_on_new_route_and_remembers_vignette() -> None:
    service = RouteService(RouteProvider(), repository())
    asyncio.run(service.plan(AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST)))
    first_generation = service.route_session_facts["session_generation"]
    requirement_id = service.active_route_requirements[0].id

    service.mark_vignette_purchased(requirement_id)
    assert service.route_session_facts["purchased_vignette_requirement_ids"] == [requirement_id]

    asyncio.run(service.plan(AssistantIntent(destination="Bratislava", priority=RoutePriority.FASTEST)))
    assert service.route_session_facts["session_generation"] == first_generation + 1
    assert service.route_session_facts["purchased_vignette_requirement_ids"] == []


def test_duplicate_vignette_purchase_is_still_completed_in_route_memory() -> None:
    service = RouteService(RouteProvider(), repository())
    asyncio.run(service.plan(AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST)))
    requirement_id = service.active_route_requirements[0].id
    commerce = CommerceService(service, WalletService())

    first = asyncio.run(commerce.purchase_vignette(service.active_route_id or "", requirement_id, "confirmed"))
    duplicate = asyncio.run(commerce.purchase_vignette(service.active_route_id or "", requirement_id, "confirmed"))

    assert first.status.value == "completed"
    assert duplicate.status.value == "duplicate"
    assert service.route_session_facts["purchased_vignette_requirement_ids"] == [requirement_id]


def test_route_session_records_complete_charging_sequence_once() -> None:
    service = RouteService(RouteProvider(), repository())
    service._active_route_id = "route-1"
    service._route_session = {
        "charging_plan_confirmed": False,
        "confirmed_charging_stop_ids": [],
        "purchased_vignette_requirement_ids": [],
        "completed_partner_opportunity_ids": [],
    }
    service.mark_partner_opportunity_completed("hotel-1")
    service.mark_partner_opportunity_completed("hotel-1")

    assert service.route_session_facts["completed_partner_opportunity_ids"] == ["hotel-1"]
