from ...models.contracts import Coordinates, RoutePriority, StopPinpoint
from ..trip.deterministic import select_route_pois
from ..trip.ports import GeocodedPlace, POIProvider, ProviderRoute, RoutingProvider


SUPPORTED_CATEGORIES = frozenset(
    {
        "charging", "hotel", "restaurant", "attraction", "coffee", "rest",
        "toilets", "fuel", "service",
    }
)


class POIService:
    def __init__(
        self, provider: POIProvider, routing_provider: RoutingProvider | None = None
    ) -> None:
        self._provider = provider
        self._routing_provider = routing_provider

    async def search(
        self,
        route: ProviderRoute,
        category: str,
        preference: str | None = None,
    ) -> list[StopPinpoint]:
        normalized_category = category.casefold()
        if normalized_category not in SUPPORTED_CATEGORIES:
            raise ValueError(f"Unsupported POI category: {category}")
        candidates = await self._provider.search_pois(
            route, normalized_category, preference
        )
        return [candidate.stop for candidate in select_route_pois(candidates, preference)]

    async def route_through(
        self,
        route: ProviderRoute,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
        stop: StopPinpoint,
    ) -> ProviderRoute:
        if self._routing_provider is None:
            raise RuntimeError("A routing provider is required to reroute through a POI")
        waypoint = GeocodedPlace(
            stop.name,
            Coordinates(lng=stop.coords[0], lat=stop.coords[1]),
        )
        del route
        return await self._routing_provider.route(
            origin, destination, priority, (waypoint,)
        )