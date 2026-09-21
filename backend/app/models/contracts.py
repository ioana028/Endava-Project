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
        "charging", "hotel", "restaurant", "attraction", "coffee", "food",
        "rest", "toilets", "fuel", "toll", "vignette", "service", "shopping"
    ]
    coords: tuple[float, float]
    rating: float | None = None
    user_review_count: int | None = Field(default=None, ge=0)
    tag: str = ""
    amenities: tuple[str, ...] = ()
    charging_power_kw: float | None = Field(default=None, ge=0)
    detour_minutes: float = Field(ge=0, default=0)
    distance_meters: float | None = Field(default=None, ge=0)
    charging_duration_minutes: float = Field(ge=0, default=0)
    mandatory: bool = False
    partner: "PartnerEnrichment | None" = None
    partner_benefit: str | None = None


class PartnerEnrichment(ContractModel):
    id: str
    name: str
    benefit: str | None = None


class BorderCrossing(ContractModel):
    from_country: str
    to_country: str


class RouteRequirement(ContractModel):
    id: str
    name: str
    country: str
    kind: Literal["toll", "vignette"]
    mandatory: bool = True


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
    border_crossings: list[BorderCrossing] = Field(default_factory=list)
    route_requirements: list[RouteRequirement] = Field(default_factory=list)
    charging_stop: StopPinpoint | None = None
    charging_required: bool = False


class RealtimeToolRouteRequest(ContractModel):
    destination: str = Field(min_length=1, max_length=200)
    priority: RoutePriority = RoutePriority.BALANCED


class RealtimeToolRouteResponse(ContractModel):
    route: RouteResponse
    route_id: str | None = None
    search_id: str | None = None


class RealtimeToolSearchRoutePoiRequest(ContractModel):
    category: str = Field(min_length=1, max_length=50)
    location: str | None = None
    preference: str | None = None


class RealtimeToolSearchRoutePoiResponse(ContractModel):
    results: list[StopPinpoint] = Field(default_factory=list)
    route_id: str | None = None
    search_id: str | None = None


class RealtimeToolSearchStopAmenitiesRequest(ContractModel):
    stop_id: str = Field(min_length=1, max_length=200)
    route_id: str = Field(min_length=1, max_length=200)
    search_id: str | None = Field(default=None, max_length=200)
    categories: list[str] = Field(default_factory=list, max_length=4)


class RealtimeToolSearchStopAmenitiesResponse(ContractModel):
    selected_stop_name: str = Field(min_length=1)
    results: list[StopPinpoint] = Field(default_factory=list, max_length=4)
    radius_meters: int = Field(default=500, ge=500, le=500)
    route_id: str
    search_id: str | None = None


class RealtimeToolConfirmChargingRequest(ContractModel):
    route_id: str = Field(min_length=1, max_length=200)
    stop_id: str | None = Field(default=None, max_length=200)
    confirmation: Literal["confirmed"]


class RealtimeToolConfirmChargingResponse(ContractModel):
    route: RouteResponse
    selected_stop_name: str
    results: list[StopPinpoint] = Field(default_factory=list, max_length=4)
    radius_meters: int = Field(default=500, ge=500, le=500)
    route_id: str
    search_id: str | None = None


class RealtimeToolRerouteRequest(ContractModel):
    poi_id: str = Field(min_length=1, max_length=200)
    route_id: str = Field(min_length=1, max_length=200)
    search_id: str = Field(min_length=1, max_length=200)
    coords: tuple[float, float] | None = None
    priority: RoutePriority | None = None
    confirmation: Literal["confirmed"]


class RealtimeToolRerouteResponse(ContractModel):
    route: RouteResponse


class RealtimeToolPurchaseVignetteRequest(ContractModel):
    route_id: str = Field(min_length=1, max_length=200)
    requirement_id: str = Field(min_length=1, max_length=200)
    confirmation: Literal["confirmed"]


class RealtimeToolPurchaseVignetteResponse(ContractModel):
    status: Literal["completed", "duplicate"]
    transaction_id: str = Field(min_length=1)
    route_id: str
    requirement_id: str
    wallet_status: Literal["ready", "processing", "completed", "declined", "duplicate"]
    phone_confirmation_status: Literal["pending", "sent", "failed"]
    amount_eur: float = Field(ge=0)
    currency: Literal["EUR"]


class RealtimeToolBookingRequest(ContractModel):
    route_id: str = Field(min_length=1, max_length=200)
    search_id: str = Field(min_length=1, max_length=200)
    result_id: str = Field(min_length=1, max_length=200)
    booking_type: Literal["hotel_room", "restaurant_table"]
    guests: int = Field(ge=1, le=20)
    date: str = Field(min_length=1, max_length=30)
    time: str | None = Field(default=None, max_length=10)
    confirmation: Literal["confirmed"]


class RealtimeToolBookingResponse(ContractModel):
    status: Literal["completed", "duplicate"]
    booking_id: str = Field(min_length=1)
    result_id: str
    route_id: str
    booking_type: Literal["hotel_room", "restaurant_table"]
    guests: int = Field(ge=1, le=20)
    date: str
    time: str | None = None
    wallet_status: Literal["ready", "processing", "completed", "declined", "duplicate"]
    phone_confirmation_status: Literal["pending", "sent", "failed"]


class RealtimeToolStartDrivingRequest(ContractModel):
    route_id: str = Field(min_length=1, max_length=200)
    confirmation: Literal["confirmed"]


class DrivingNextStop(ContractModel):
    id: str
    name: str
    category: Literal[
        "charging", "hotel", "restaurant", "attraction", "coffee", "food",
        "rest", "toilets", "fuel", "toll", "vignette", "service", "shopping"
    ]


class RealtimeToolStartDrivingResponse(ContractModel):
    status: Literal["active"]
    route_id: str
    remaining_distance_km: float = Field(ge=0)
    remaining_duration_minutes: float = Field(ge=0)
    eta: str = Field(min_length=1)
    next_stop: DrivingNextStop | None = None
    charging_required: bool


class RealtimeToolReturnToMainRouteRequest(ContractModel):
    route_id: str = Field(min_length=1, max_length=200)


class RealtimeToolReturnToMainRouteResponse(ContractModel):
    status: Literal["success"]
    route_id: str


class RealtimeSessionResponse(ContractModel):
    client_secret: str = Field(min_length=1)
    model: str = Field(min_length=1)


class HealthResponse(ContractModel):
    status: str
    service: str
    environment: str


class ProviderHealthResponse(ContractModel):
    status: str
    environment: str
    openai_configured: bool
    google_routes_configured: bool
    google_places_configured: bool
    places_provider: str
    scenic_capability: bool = False
    partner_enrichment_ready: bool = False


class VehicleTelemetryResponse(ContractModel):
    vehicle_id: str
    propulsion: Literal["BEV"]
    battery_percent: float = Field(ge=0, le=100)
    estimated_range_km: float = Field(ge=0)
    max_charged_range_km: float = Field(ge=0)
    consumption_rate_kwh: float = Field(gt=0)
    tyres: Literal["SUMMER", "WINTER", "ALL_SEASON"]
    odometer_km: float = Field(ge=0)