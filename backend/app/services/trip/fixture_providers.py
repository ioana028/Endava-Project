from collections.abc import Iterable

from ...models.contracts import StopPinpoint
from ...models.fixtures import Partner
from .ports import ChargingCandidate, POICandidate, ProviderRoute


class FixtureChargingProvider:
    def __init__(self, partners: Iterable[Partner]) -> None:
        self._partners = tuple(partners)

    async def search_charging(
        self, route: ProviderRoute, max_distance_km: float
    ) -> tuple[ChargingCandidate, ...]:
        del route
        return tuple(
            ChargingCandidate(
                stop=StopPinpoint(
                    id=partner.id,
                    name=partner.name,
                    category="charging",
                    coords=partner.coords,
                    rating=partner.rating,
                    tag=partner.tag,
                    detour_minutes=partner.detour_minutes,
                    charging_duration_minutes=partner.charging_duration_minutes,
                ),
                distance_from_route_km=min(max_distance_km, 1),
                charging_duration_minutes=partner.charging_duration_minutes,
            )
            for partner in self._partners
            if partner.category == "charging"
        )


class FixturePOIProvider:
    def __init__(self, partners: Iterable[Partner]) -> None:
        self._partners = tuple(partners)

    async def search_pois(
        self, route: ProviderRoute, category: str, preference: str | None
    ) -> tuple[POICandidate, ...]:
        del route, preference
        category_aliases = {"restaurant": {"restaurant", "food"}}
        accepted_categories = category_aliases.get(category, {category})
        return tuple(
            POICandidate(
                stop=StopPinpoint(
                    id=partner.id,
                    name=partner.name,
                    category=category,
                    coords=partner.coords,
                    rating=partner.rating,
                    tag=partner.tag,
                    detour_minutes=partner.detour_minutes,
                ),
                route_relevance=1,
                quality=partner.rating or 0,
            )
            for partner in self._partners
            if partner.category in accepted_categories
        )