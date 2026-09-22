import asyncio
from pathlib import Path

from backend.app.core.fixture_repository import FixtureRepository
from backend.app.models.contracts import AssistantIntent, RoutePriority, StopPinpoint
from backend.app.services.trip.deterministic import (
    estimate_charging_duration_minutes,
    select_chargers_iteratively,
)
from backend.app.services.trip.ports import ChargingCandidate
from backend.app.services.trip.service import RouteService
from backend.app.services.vehicle.service import VehicleTelemetryService
from tests.backend.unit.test_route_service import FakeRoutingProvider


def repository(**telemetry_updates: float) -> FixtureRepository:
    fixture_repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"), Path("data/partners/partners.json")
    )
    fixtures = fixture_repository.load()
    fixture_repository._fixtures = fixtures.model_copy(
        update={"telemetry": fixtures.telemetry.model_copy(update=telemetry_updates)}
    )
    return fixture_repository


def test_active_telemetry_drives_battery_range_and_consumption_facts() -> None:
    fixture_repository = repository(
        battery_percent=63,
        estimated_range_km=80,
        max_charged_range_km=180,
        consumption_rate_kwh=20,
    )
    telemetry = VehicleTelemetryService(fixture_repository)
    service = RouteService(FakeRoutingProvider(distance_meters=90_000), fixture_repository)

    route = asyncio.run(
        service.plan(AssistantIntent(destination="Bratislava", priority=RoutePriority.FASTEST))
    )

    assert telemetry.battery_percent == 63
    assert telemetry.estimated_range_km == 80
    assert telemetry.max_charged_range_km == 180
    assert telemetry.consumption_rate_kwh == 20
    assert route.charging_required is True
    assert route.alerts == []
    assert service.route_state_facts()["remaining_distance_km"] == 90


def test_max_charged_range_is_used_after_the_first_leg() -> None:
    def candidate(stop_id: str, progress_km: float) -> ChargingCandidate:
        return ChargingCandidate(
            stop=StopPinpoint(
                id=stop_id,
                name=stop_id,
                category="charging",
                coords=(16 + progress_km / 100, 48),
            ),
            distance_from_origin_km=progress_km,
        )

    plan = select_chargers_iteratively(
        [candidate("first", 70), candidate("second", 220)],
        route_distance_km=300,
        vehicle_range_km=80,
        safety_buffer_km=10,
        max_charged_range_km=250,
    )

    assert plan is not None
    assert [item.stop.id for item in plan] == ["first"]


def test_consumption_rate_changes_computed_charging_duration() -> None:
    candidate = ChargingCandidate(
        stop=StopPinpoint(
            id="charger",
            name="charger",
            category="charging",
            coords=(17, 48),
        ),
        distance_from_origin_km=70,
        charging_power_kw=50,
    )

    low_consumption = estimate_charging_duration_minutes(
        candidate, 200, 70, 80, 10, 16
    )
    high_consumption = estimate_charging_duration_minutes(
        candidate, 200, 70, 80, 10, 20
    )

    assert high_consumption > low_consumption
