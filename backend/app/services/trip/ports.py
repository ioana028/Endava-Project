from dataclasses import dataclass
from typing import Protocol

from ...models.contracts import Coordinates, RoutePriority, StopPinpoint


class InvalidDestinationError(ValueError):
    """Raised when a routing provider cannot resolve a place."""


class RoutingProviderError(RuntimeError):
    """Raised when a routing provider cannot complete a request."""


@dataclass(frozen=True, slots=True)
class GeocodedPlace:
    display_name: str
    coordinates: Coordinates


@dataclass(frozen=True, slots=True)
class ProviderRoute:
    distance_meters: float
    duration_seconds: float
    geometry: tuple[tuple[float, float], ...]
    countries: tuple[str, ...] = ()
    border_crossings: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ChargingCandidate:
    stop: StopPinpoint
    compatible: bool = True
    available: bool = True
    distance_from_route_km: float = 0


@dataclass(frozen=True, slots=True)
class POICandidate:
    stop: StopPinpoint
    route_relevance: float = 0
    quality: float = 0


class ChargingProvider(Protocol):
    async def search_charging(
        self, route: ProviderRoute, max_distance_km: float
    ) -> tuple[ChargingCandidate, ...]: ...


class POIProvider(Protocol):
    async def search_pois(
        self, route: ProviderRoute, category: str, preference: str | None
    ) -> tuple[POICandidate, ...]: ...


class RoutingProvider(Protocol):
    async def geocode(self, place: str) -> GeocodedPlace: ...

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
        waypoints: tuple[GeocodedPlace, ...] = (),
    ) -> ProviderRoute: ...