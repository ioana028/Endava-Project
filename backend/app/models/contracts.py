from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class RoutePriority(StrEnum):
    FASTEST = "FASTEST"
    CHEAPEST = "CHEAPEST"
    SCENIC = "SCENIC"
    BALANCED = "BALANCED"


class AssistantIntent(ContractModel):
    destination: str = Field(min_length=1)
    priority: RoutePriority


class Coordinates(ContractModel):
    lng: float
    lat: float


class StopPinpoint(ContractModel):
    id: str
    name: str
    category: Literal[
        "charging",
        "food",
        "rest",
        "toll",
        "vignette",
        "service",
        "hotel",
        "restaurant",
        "attraction",
        "coffee",
    ]
    coords: tuple[float, float]
    rating: float | None = None
    tag: str
    detour_minutes: float = Field(ge=0)
    partner_benefit: str | None = None


class TripStats(ContractModel):
    total_distance_km: float = Field(ge=0)
    driving_duration_minutes: float = Field(ge=0, default=0)
    total_duration_minutes: float = Field(ge=0)
    total_price_eur: float = Field(ge=0, default=0)


class RouteAlert(ContractModel):
    type: Literal["WEATHER", "TRAFFIC", "TOLL", "VEHICLE"]
    location_name: str | None = None
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    message: str = Field(min_length=1)


class RouteResponse(ContractModel):
    origin: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    stats: TripStats
    geometry: list[tuple[float, float]]
    stops: list[StopPinpoint] = Field(default_factory=list)
    alerts: list[RouteAlert] = Field(default_factory=list)
    charging_stop: StopPinpoint | None = None
    border_crossings: list[str] = Field(default_factory=list)
    route_requirements: list[str] = Field(default_factory=list)


class RealtimeToolRouteRequest(ContractModel):
    destination: str = Field(min_length=1, max_length=200)
    priority: RoutePriority


class RealtimeToolRouteResponse(ContractModel):
    route: RouteResponse


class RealtimeToolSearchRoutePoiRequest(ContractModel):
    category: str = Field(min_length=1, max_length=50)
    location: str | None = None
    preference: str | None = None


class RealtimeToolSearchRoutePoiResponse(ContractModel):
    results: list[StopPinpoint] = Field(default_factory=list)


class RealtimeSessionResponse(ContractModel):
    client_secret: str = Field(min_length=1)
    model: str = Field(min_length=1)


class HealthResponse(ContractModel):
    status: str
    service: str
    environment: str