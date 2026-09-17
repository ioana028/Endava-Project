from __future__ import annotations

import json
from pathlib import Path

from ...core.fixture_repository import FixtureRepository
from ...models.contracts import StopPinpoint
from ...services.trip.ports import ProviderRoute


class LocalPlacesProvider:
    def __init__(
        self,
        fixture_repository: FixtureRepository,
        places_path: Path | None = None,
    ) -> None:
        self._fixture_repository = fixture_repository
        self._places_path = places_path or Path(__file__).resolve().parents[4] / "data" / "places" / "places.json"
        self._generic_pois = self._load_generic_pois()

    async def search(
        self,
        category: str,
        location: str | None = None,
        preference: str | None = None,
        route: ProviderRoute | None = None,
        near_coords: tuple[float, float] | None = None,
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

        location_context = (location or "destination").strip().lower()
        if location_context not in {"route", "stop", "destination"}:
            location_context = "destination"

        candidates = [
            candidate
            for candidate in candidates
            if self._matches_location(candidate, location_context, route)
            and self._matches_search_center(candidate, near_coords, location_context)
        ]
        candidates.sort(
            key=lambda candidate: (
                self._route_distance(candidate, location_context, route),
                candidate.detour_minutes,
                -(candidate.rating or 0),
                candidate.name,
            )
        )
        return candidates[:10]

    @staticmethod
    def _matches_search_center(
        candidate: StopPinpoint,
        near_coords: tuple[float, float] | None,
        location: str | None = None,
    ) -> bool:
        if near_coords is None:
            return True
        longitude_delta = (candidate.coords[0] - near_coords[0]) * 70
        latitude_delta = (candidate.coords[1] - near_coords[1]) * 111
        limit_km = 0.5 if (location or "destination") == "stop" else 5.0
        return (longitude_delta**2 + latitude_delta**2) ** 0.5 <= limit_km

    @staticmethod
    def _matches_location(
        candidate: StopPinpoint,
        location: str,
        route: ProviderRoute | None,
    ) -> bool:
        if route is None or not route.geometry:
            return True
        if location == "stop":
            return True
        distance = LocalPlacesProvider._route_distance(candidate, location, route)
        if location == "route":
            return distance <= 7.5
        return distance <= 10.0

    @staticmethod
    def _route_distance(
        candidate: StopPinpoint,
        location: str,
        route: ProviderRoute | None,
    ) -> float:
        if route is None or not route.geometry:
            return 0
        point = candidate.coords
        if location == "destination":
            reference = route.geometry[-1]
            return LocalPlacesProvider._distance(point, reference)
        if location == "stop":
            reference_points = route.geometry[1:-1] or route.geometry
            return min(
                LocalPlacesProvider._distance(point, reference)
                for reference in reference_points
            )
        return min(
            LocalPlacesProvider._distance_to_segment(point, start, end)
            for start, end in zip(route.geometry, route.geometry[1:])
        )

    @staticmethod
    def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
        longitude_delta = first[0] - second[0]
        latitude_delta = first[1] - second[1]
        return (longitude_delta**2 + latitude_delta**2) ** 0.5

    @staticmethod
    def _distance_to_segment(
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        segment_longitude = end[0] - start[0]
        segment_latitude = end[1] - start[1]
        length_squared = segment_longitude**2 + segment_latitude**2
        if length_squared == 0:
            return LocalPlacesProvider._distance(point, start)

        projection = (
            (point[0] - start[0]) * segment_longitude
            + (point[1] - start[1]) * segment_latitude
        ) / length_squared
        projection = max(0, min(1, projection))
        closest = (
            start[0] + projection * segment_longitude,
            start[1] + projection * segment_latitude,
        )
        return LocalPlacesProvider._distance(point, closest)

    def _partner_matches(self, category: str) -> list[StopPinpoint]:
        partners = self._fixture_repository.fixtures.partners
        results: list[StopPinpoint] = []
        for partner in partners:
            if partner.kind != "location" or partner.coords is None:
                continue
            if category == "food" and partner.category in {"food", "restaurant"}:
                results.append(self._partner_to_stop(partner))
                continue
            if partner.category == category:
                results.append(self._partner_to_stop(partner))
        return results

    def _generic_matches(self, category: str) -> list[StopPinpoint]:
        results: list[StopPinpoint] = []
        for item in self._generic_pois:
            accepted_categories = {category}
            if category == "food":
                accepted_categories.update({"food", "restaurant"})
            if item["category"] not in accepted_categories:
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

    def _load_generic_pois(self) -> tuple[dict[str, object], ...]:
        try:
            with self._places_path.open(encoding="utf-8") as fixture_file:
                records = json.load(fixture_file)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("Unable to load offline Places fixtures") from error
        if not isinstance(records, list):
            raise RuntimeError("Offline Places fixtures must be a JSON array")
        return tuple(record for record in records if isinstance(record, dict))

    def _partner_to_stop(self, partner: object) -> StopPinpoint:
        tag = partner.tag
        partner_benefit = None
        tag_lower = tag.lower()
        if partner.category != "vignette" and any(
            keyword in tag_lower for keyword in ("discount", "rate", "benefit")
        ):
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
            "toilet": "toilets",
            "toilets": "toilets",
            "shopping": "shopping",
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


OfflinePlacesProvider = LocalPlacesProvider
