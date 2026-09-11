from dataclasses import dataclass
from typing import Protocol

from ...models.contracts import Coordinates, RoutePriority


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


class RoutingProvider(Protocol):
    async def geocode(self, place: str) -> GeocodedPlace: ...

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
    ) -> ProviderRoute: ...