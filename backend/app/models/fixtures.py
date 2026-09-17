from typing import Literal

from pydantic import Field

from .contracts import ContractModel


class VehicleState(ContractModel):
    vehicle_id: str
    propulsion: Literal["BEV"]
    battery_percent: float = Field(ge=0, le=100)
    estimated_range_km: float = Field(ge=0)
    max_charged_range_km: float = Field(default=0, ge=0)
    consumption_rate_kwh: float = Field(gt=0)
    tyres: Literal["SUMMER", "WINTER", "ALL_SEASON"]
    odometer_km: float = Field(ge=0)


class Partner(ContractModel):
    id: str
    kind: Literal["location", "network"] = "location"
    name: str
    brand: str | None = None
    category: Literal[
        "charging", "hotel", "restaurant", "attraction", "coffee", "food",
        "rest", "toilets", "fuel", "toll", "vignette", "service"
    ]
    categories: tuple[str, ...] = ()
    coords: tuple[float, float] | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    tag: str = ""
    benefit: str | None = None
    amenities: tuple[str, ...] = ()
    provider_brands: tuple[str, ...] = ()
    enabled: bool = True
    detour_minutes: int = Field(default=0, ge=0)
    charging_duration_minutes: float = Field(ge=0, default=0)


class Fixtures(ContractModel):
    telemetry: VehicleState
    partners: tuple[Partner, ...]