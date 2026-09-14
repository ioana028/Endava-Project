from __future__ import annotations

from ...core.fixture_repository import FixtureRepository
from ...models.contracts import StopPinpoint


class LocalPlacesProvider:
    _GENERIC_POIS = (
        {
            "id": "hotel-route-view",
            "name": "RouteView Hotel",
            "category": "hotel",
            "coords": (19.0409, 47.4988),
            "rating": 4.6,
            "tag": "Boutique stay near the route",
            "detour_minutes": 6,
        },
        {
            "id": "restaurant-italia-budapest",
            "name": "Italia Ristorante",
            "category": "restaurant",
            "coords": (19.0531, 47.4987),
            "rating": 4.8,
            "tag": "Italian dining near the destination",
            "detour_minutes": 3,
        },
        {
            "id": "attraction-riverfront",
            "name": "Riverfront Walk",
            "category": "attraction",
            "coords": (19.0438, 47.5000),
            "rating": 4.4,
            "tag": "Scenic attraction near the destination",
            "detour_minutes": 4,
        },
        {
            "id": "coffee-route-stop",
            "name": "Route Café",
            "category": "coffee",
            "coords": (18.2300, 47.9000),
            "rating": 4.5,
            "tag": "Coffee stop on the motorway",
            "detour_minutes": 2,
        },
        {
            "id": "rest-area-boost",
            "name": "Boost Rest Area",
            "category": "rest",
            "coords": (18.1600, 47.7200),
            "rating": 4.3,
            "tag": "Rest stop and toilets",
            "detour_minutes": 1,
        },
        {
            "id": "service-point-safety",
            "name": "Safety Service Point",
            "category": "service",
            "coords": (18.3300, 47.8400),
            "rating": 4.2,
            "tag": "Vehicle support and service",
            "detour_minutes": 2,
        },
    )

    def __init__(self, fixture_repository: FixtureRepository) -> None:
        self._fixture_repository = fixture_repository

    async def search(
        self,
        category: str,
        location: str | None = None,
        preference: str | None = None,
    ) -> list[StopPinpoint]:
        normalized = self._normalize_category(category)

        candidates: list[StopPinpoint] = []
        candidates.extend(self._partner_matches(normalized))
        candidates.extend(self._generic_matches(normalized))

        if preference:
            preference_lower = preference.lower()
            candidates = [
                candidate
                for candidate in candidates
                if preference_lower in candidate.name.lower()
                or preference_lower in candidate.tag.lower()
            ]

        location_text = (location or "").lower()
        candidates.sort(
            key=lambda candidate: (
                0 if location_text and location_text in candidate.name.lower() else 1,
                candidate.detour_minutes,
                -(candidate.rating or 0),
                candidate.name,
            )
        )
        return candidates[:10]

    def _partner_matches(self, category: str) -> list[StopPinpoint]:
        partners = self._fixture_repository.fixtures.partners
        results: list[StopPinpoint] = []
        for partner in partners:
            if category == "food" and partner.category == "food":
                results.append(self._partner_to_stop(partner))
                continue
            if partner.category == category:
                results.append(self._partner_to_stop(partner))
        return results

    def _generic_matches(self, category: str) -> list[StopPinpoint]:
        results: list[StopPinpoint] = []
        for item in self._GENERIC_POIS:
            if item["category"] != category:
                continue
            results.append(
                StopPinpoint(
                    id=item["id"],
                    name=item["name"],
                    category=item["category"],
                    coords=item["coords"],
                    rating=item["rating"],
                    tag=item["tag"],
                    detour_minutes=item["detour_minutes"],
                )
            )
        return results

    def _partner_to_stop(self, partner: object) -> StopPinpoint:
        tag = partner.tag
        partner_benefit = None
        tag_lower = tag.lower()
        if any(keyword in tag_lower for keyword in ("discount", "rate", "benefit")):
            partner_benefit = tag

        return StopPinpoint(
            id=partner.id,
            name=partner.name,
            category=partner.category,
            coords=(partner.coords[0], partner.coords[1]),
            rating=partner.rating,
            tag=tag,
            detour_minutes=float(partner.detour_minutes),
            partner_benefit=partner_benefit,
        )

    @staticmethod
    def _normalize_category(category: str) -> str:
        normalized = category.strip().lower()
        aliases = {
            "hotel": "hotel",
            "hotels": "hotel",
            "restaurant": "restaurant",
            "restaurants": "restaurant",
            "food": "food",
            "attraction": "attraction",
            "attractions": "attraction",
            "coffee": "coffee",
            "rest": "rest",
            "service": "service",
            "charger": "charging",
            "charging": "charging",
            "charge": "charging",
            "toll": "toll",
            "vignette": "vignette",
        }
        if normalized not in aliases:
            raise ValueError(f"Unsupported POI category: {category}")
        return aliases[normalized]
