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
    category: Literal["charging", "food", "rest", "toll", "vignette", "service"]
    coords: tuple[float, float]
    rating: float | None = None
    tag: str
    detour_minutes: float = Field(ge=0)


class TripStats(ContractModel):
    total_distance_km: float = Field(ge=0)
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


class AssistantResponse(ContractModel):
    transcript: str
    intent: AssistantIntent
    spoken_response: str
    audio_base64: str | None = None
    route: RouteResponse | None = None
    toast_message: str | None = None


class InteractRequest(ContractModel):
    text: str = Field(min_length=1)
    session_id: str | None = None


class HealthResponse(ContractModel):
    status: str
    service: str
    environment: str