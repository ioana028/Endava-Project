from dataclasses import dataclass
from collections.abc import Iterable

from ...models.contracts import Coordinates, RoutePriority, StopPinpoint
from ..trip.deterministic import select_route_pois
from ..trip.deterministic import distance_to_route_km
from ..trip.ports import GeocodedPlace, POIProvider, ProviderRoute, RoutingProvider


SUPPORTED_CATEGORIES = frozenset(
    {
        "charging", "hotel", "restaurant", "attraction", "coffee", "rest",
        "toilets", "fuel", "service",
    }
)


@dataclass(frozen=True, slots=True)
class PartnerOpportunity:
    id: str
    stop: StopPinpoint
    reason: str
    detour_minutes: float
    requires_route_confirmation: bool = True
    score: float = 0.0


def rank_partner_opportunities(
    stops: Iterable[StopPinpoint],
    geometry: tuple[tuple[float, float], ...],
    safe_stop_ids: Iterable[str] | None = None,
    max_results: int = 2,
) -> list[PartnerOpportunity]:
    """Return a small, deterministic list of safe, verified partner suggestions."""
    safe_ids = set(safe_stop_ids) if safe_stop_ids is not None else None
    ranked: list[PartnerOpportunity] = []
    for stop in stops:
        if not stop.partner or not stop.partner_benefit:
            continue
        if safe_ids is not None and stop.id not in safe_ids:
            continue
        route_relevance = 1 / (1 + distance_to_route_km(stop.coords, geometry))
        benefit_relevance = 1.0 if stop.partner_benefit else 0.0
        score = (
            route_relevance * 5
            + benefit_relevance * 2
            + (stop.rating or 0) * 0.25
            - stop.detour_minutes * 0.2
        )
        ranked.append(
            PartnerOpportunity(
                id=f"partner-opportunity-{stop.id}",
                stop=stop,
                reason=f"Verified demo partner benefit: {stop.partner_benefit}",
                detour_minutes=stop.detour_minutes,
                score=score,
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.detour_minutes, item.stop.id))
    return ranked[: max(0, max_results)]


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