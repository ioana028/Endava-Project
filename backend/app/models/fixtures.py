from typing import Literal

from pydantic import Field

from .contracts import ContractModel


class VehicleState(ContractModel):
    vehicle_id: str
    propulsion: Literal["BEV"]
    battery_percent: float = Field(ge=0, le=100)
    estimated_range_km: float = Field(ge=0)
    consumption_rate_kwh: float = Field(gt=0)
    tyres: Literal["SUMMER", "WINTER", "ALL_SEASON"]
    odometer_km: float = Field(ge=0)


class Partner(ContractModel):
    id: str
    name: str
    category: Literal["charging", "food", "rest", "toll", "vignette", "service"]
    coords: tuple[float, float]
    rating: float | None = Field(default=None, ge=0, le=5)
    tag: str
    detour_minutes: int = Field(ge=0)


class Fixtures(ContractModel):
    telemetry: VehicleState
    partners: tuple[Partner, ...]