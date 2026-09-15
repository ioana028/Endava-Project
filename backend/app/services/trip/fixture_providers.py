from collections.abc import Iterable

from ...models.contracts import StopPinpoint
from ...models.fixtures import Partner
from .deterministic import POI_CORRIDOR_RADIUS_KM, distance_to_route_km
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
        category_aliases = {
            "restaurant": {"restaurant", "food"},
            "food": {"restaurant", "food"},
            "coffee": {"coffee", "fuel", "service", "rest"},
            "rest": {"rest", "fuel", "service", "toilets"},
        }
        accepted_categories = category_aliases.get(category, {category})
        preference_lower = (preference or "").casefold()
        candidates: list[POICandidate] = []
        for partner in self._partners:
            if partner.category not in accepted_categories:
                continue
            amenities = tuple(amenity.casefold() for amenity in partner.amenities)
            if category == "coffee" and partner.category in {"fuel", "service", "rest"}:
                if not any(
                    item in amenities for item in ("coffee", "cafe", "convenience", "food")
                ):
                    continue
            if category == "rest" and partner.category in {"fuel", "service"}:
                if not any(
                    item in amenities
                    for item in ("rest", "toilets", "convenience", "food", "service")
                ):
                    continue
            corridor_distance = distance_to_route_km(partner.coords, tuple(route.geometry))
            if corridor_distance > POI_CORRIDOR_RADIUS_KM:
                continue
            stop_category = category if category in {"coffee", "rest"} else partner.category
            candidates.append(
                POICandidate(
                    stop=StopPinpoint(
                        id=partner.id,
                        name=partner.name,
                        category=stop_category,
                        coords=partner.coords,
                        rating=partner.rating,
                        tag=partner.tag,
                        amenities=partner.amenities,
                        detour_minutes=partner.detour_minutes,
                    ),
                    route_relevance=1 / (1 + corridor_distance),
                    quality=(partner.rating or 0)
                    + (
                        1
                        if preference_lower and preference_lower in partner.name.casefold()
                        else 0
                    ),
                )
            )
        return tuple(candidates)