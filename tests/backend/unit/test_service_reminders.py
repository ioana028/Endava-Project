from pathlib import Path

from backend.app.core.fixture_repository import FixtureRepository
from backend.app.services.trip.service import RouteService
from backend.app.services.vehicle.service import VehicleTelemetryService


class UnusedRoutingProvider:
    pass


def repository() -> FixtureRepository:
    fixture_repository = FixtureRepository(
        Path("data/vehicles/telemetry.json"),
        Path("data/partners/partners.json"),
    )
    fixture_repository.load()
    return fixture_repository


def test_service_status_distinguishes_up_to_date_due_on_route_and_overdue() -> None:
    fixture_repository = repository()
    telemetry = VehicleTelemetryService(fixture_repository)

    assert telemetry.service_status(100).status == "UP_TO_DATE"
    assert telemetry.service_status(250).status == "DUE_DURING_JOURNEY"

    fixtures = fixture_repository.fixtures
    fixture_repository._fixtures = fixtures.model_copy(
        update={
            "telemetry": fixtures.telemetry.model_copy(
                update={"odometer_km": 15025}
            )
        }
    )
    assert telemetry.service_status().status == "OVERDUE"


def test_route_service_emits_service_reminder_only_once_per_journey() -> None:
    service = RouteService(UnusedRoutingProvider(), repository())

    reminder = service.next_service_reminder(250)

    assert reminder is not None
    assert reminder.status == "DUE_DURING_JOURNEY"
    assert service.next_service_reminder(250) is None