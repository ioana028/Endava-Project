import asyncio
from pathlib import Path

import pytest

from backend.app.core.errors import APIError
from backend.app.core.fixture_repository import FixtureRepository
from backend.app.models.contracts import AssistantIntent, Coordinates, RoutePriority, StopPinpoint
from backend.app.services.trip.ports import ChargingCandidate, GeocodedPlace, ProviderRoute
from backend.app.services.trip.service import RouteService


class RigaRoutingProvider:
    async def geocode(self, place: str) -> GeocodedPlace:
        coordinates = Coordinates(lng=24.1052, lat=56.9496) if place == "Riga" else Coordinates(lng=16.37, lat=48.20)
        return GeocodedPlace(place, coordinates)

    async def route(self, origin, destination, priority, waypoints=()):
        del origin, destination, priority, waypoints
        return ProviderRoute(
            distance_meters=850_000,
            duration_seconds=31_000,
            geometry=((16.37, 48.20), (24.1052, 56.9496)),
        )


class RigaChargingProvider:
    async def search_charging(self, route, max_distance_km):
        del route, max_distance_km
        return (
            ChargingCandidate(
                stop=StopPinpoint(
                    id="riga-too-far",
                    name="Riga charger",
                    category="charging",
                    coords=(20.8, 52.5),
                ),
                distance_from_origin_km=500,
            ),
        )


def repository() -> FixtureRepository:
    repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"), Path("data/partners/partners.json")
    )
    repository.load()
    return repository


def test_riga_returns_stable_unavailable_error_when_no_safe_sequence_exists() -> None:
    service = RouteService(
        RigaRoutingProvider(),
        repository(),
        charging_provider=RigaChargingProvider(),
    )

    with pytest.raises(APIError) as error:
        asyncio.run(
            service.plan(
                AssistantIntent(destination="Riga", priority=RoutePriority.FASTEST)
            )
        )

    assert error.value.status_code == 422
    assert error.value.code == "NO_SAFE_CHARGING_PLAN"
    assert "safe sequence" in error.value.message
    assert service.active_route_id is None


def test_confirmation_returns_complete_ordered_plan_and_session_state() -> None:
    from tests.backend.unit.test_day8_route_memory import RouteProvider, repository as loaded_repository

    service = RouteService(RouteProvider(), loaded_repository())
    asyncio.run(
        service.plan(
            AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST)
        )
    )
    result = asyncio.run(service.confirm_charging_stop(service.active_route_id or ""))

    assert result["charging_plan"].complete is True
    assert result["charging_plan"].confirmed is True
    assert result["charging_plan"].stops[0].id == "tea-sopron"
    assert result["session_facts"].charging_plan_confirmed is True
    assert result["route"].charging_plan.total_charging_minutes > 0


def test_completed_charging_stop_is_not_requested_again() -> None:
    from tests.backend.unit.test_day8_route_memory import RouteProvider, repository as loaded_repository

    service = RouteService(RouteProvider(), loaded_repository())
    asyncio.run(
        service.plan(
            AssistantIntent(destination="Budapest", priority=RoutePriority.FASTEST)
        )
    )
    route_id = service.active_route_id or ""
    asyncio.run(service.confirm_charging_stop(route_id))
    service.mark_charging_stop_completed("tea-sopron")
    service.mark_charging_stop_completed("tea-sopron")

    facts = service.route_state_facts()
    assert facts["charging_plan_status"] == "completed"
    assert service.route_session_facts["completed_charging_stop_ids"] == ["tea-sopron"]
    assert service.next_mandatory_stop() is None
