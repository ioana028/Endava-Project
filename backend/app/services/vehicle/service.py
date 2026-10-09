from ...core.fixture_repository import FixtureRepository
from ...models.contracts import VehicleServiceStatus
from ...models.fixtures import VehicleState


class VehicleTelemetryService:
    """Single source for the active vehicle telemetry used by trip policy."""

    def __init__(self, fixture_repository: FixtureRepository) -> None:
        self._fixture_repository = fixture_repository

    @property
    def current(self) -> VehicleState:
        return self._fixture_repository.fixtures.telemetry

    @property
    def battery_percent(self) -> float:
        return self.current.battery_percent

    @property
    def estimated_range_km(self) -> float:
        return self.current.estimated_range_km

    @property
    def max_charged_range_km(self) -> float:
        return self.current.max_charged_range_km

    @property
    def consumption_rate_kwh(self) -> float:
        return self.current.consumption_rate_kwh

    @property
    def connector_types(self) -> tuple[str, ...]:
        return self.current.connector_types

    @property
    def max_charging_power_kw(self) -> float:
        return self.current.max_charging_power_kw

    @property
    def battery_capacity_kwh(self) -> float:
        return self.current.battery_capacity_kwh

    def service_status(self, journey_distance_km: float = 0) -> VehicleServiceStatus:
        next_service_odometer_km = (
            self.current.last_service_odometer_km
            + self.current.service_interval_km
        )
        due_in_km = next_service_odometer_km - self.current.odometer_km
        if due_in_km <= 0:
            status = "OVERDUE"
        elif due_in_km <= journey_distance_km:
            status = "DUE_DURING_JOURNEY"
        else:
            status = "UP_TO_DATE"
        return VehicleServiceStatus(
            status=status,
            odometer_km=self.current.odometer_km,
            next_service_odometer_km=next_service_odometer_km,
            due_in_km=round(due_in_km, 1),
        )
