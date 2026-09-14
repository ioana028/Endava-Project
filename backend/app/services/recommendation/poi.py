from ...models.contracts import StopPinpoint
from ..trip.deterministic import rank_pois
from ..trip.ports import POIProvider, ProviderRoute


SUPPORTED_CATEGORIES = frozenset(
    {"charging", "hotel", "restaurant", "attraction", "coffee", "rest", "service"}
)


class POIService:
    def __init__(self, provider: POIProvider) -> None:
        self._provider = provider

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
        return [candidate.stop for candidate in rank_pois(candidates, preference)]