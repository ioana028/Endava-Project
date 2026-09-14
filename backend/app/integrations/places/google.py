from __future__ import annotations

import math

import httpx

from ...models.contracts import StopPinpoint
from ...services.trip.ports import JourneyProviderError, ProviderRoute


PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


class GooglePlacesProvider:
    _CATEGORY_QUERIES = {
        "hotel": "hotels",
        "restaurant": "restaurants",
        "food": "restaurants and places to eat",
        "attraction": "tourist attractions and interesting places to see",
        "charging": "electric vehicle charging stations",
        "coffee": "coffee shops and cafes",
        "rest": "rest areas and service areas",
        "service": "vehicle service and repair shops",
    }

    def __init__(self, api_key: str, timeout_seconds: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search(
        self,
        category: str,
        location: str | None = None,
        preference: str | None = None,
        route: ProviderRoute | None = None,
    ) -> list[StopPinpoint]:
        normalized = self._normalize_category(category)
        if route is None or len(route.geometry) < 2:
            return []

        query = self._CATEGORY_QUERIES[normalized]
        if preference:
            query = f"{preference} {query}"
        radius = 2500 if location != "destination" else 5000
        results: dict[str, StopPinpoint] = {}

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                for longitude, latitude in self._search_points(route, location):
                    response = await client.post(
                        PLACES_SEARCH_URL,
                        json={
                            "textQuery": query,
                            "languageCode": "en",
                            "maxResultCount": 10,
                            "locationBias": {
                                "circle": {
                                    "center": {
                                        "latitude": latitude,
                                        "longitude": longitude,
                                    },
                                    "radius": radius,
                                }
                            },
                        },
                        headers={
                            "X-Goog-Api-Key": self._api_key,
                            "X-Goog-FieldMask": (
                                "places.id,places.displayName,places.location,places.types,"
                                "places.rating,places.editorialSummary,places.formattedAddress"
                            ),
                        },
                    )
                    response.raise_for_status()
                    for place in response.json().get("places", []):
                        stop = self._to_stop(place, normalized, route)
                        if stop is not None:
                            results[stop.id] = stop
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise JourneyProviderError("Google Places search failed") from error

        return sorted(
            results.values(),
            key=lambda stop: (stop.detour_minutes, -(stop.rating or 0), stop.name),
        )[:10]

    def _to_stop(
        self, place: dict[str, object], category: str, route: ProviderRoute
    ) -> StopPinpoint | None:
        try:
            place_id = str(place["id"])
            display_name = place["displayName"]
            name = str(display_name["text"])
            location = place["location"]
            coords = (float(location["longitude"]), float(location["latitude"]))
        except (KeyError, TypeError, ValueError):
            return None

        route_distance_km = self._route_distance_km(coords, route.geometry)
        if route_distance_km > 3:
            return None
        rating = place.get("rating")
        summary = place.get("editorialSummary") or {}
        address = place.get("formattedAddress")
        tag = str(summary.get("text") or address or "Google Maps place")
        return StopPinpoint(
            id=place_id,
            name=name,
            category=category,
            coords=coords,
            rating=float(rating) if rating is not None else None,
            tag=tag,
            detour_minutes=round(route_distance_km, 1),
        )

    def _search_points(
        self, route: ProviderRoute, location: str | None
    ) -> tuple[tuple[float, float], ...]:
        geometry = route.geometry
        if location == "destination":
            return (geometry[-1],)
        point_count = min(8, max(3, math.ceil(len(geometry) / 8)))
        indices = [
            round(index * (len(geometry) - 1) / (point_count - 1))
            for index in range(point_count)
        ]
        return tuple(geometry[index] for index in dict.fromkeys(indices))

    @classmethod
    def _route_distance_km(
        cls, point: tuple[float, float], geometry: tuple[tuple[float, float], ...]
    ) -> float:
        return min(
            cls._distance_to_segment_km(point, start, end)
            for start, end in zip(geometry, geometry[1:])
        )

    @staticmethod
    def _distance_to_segment_km(
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        latitude = math.radians((start[1] + end[1] + point[1]) / 3)
        scale_x = 111.32 * math.cos(latitude)
        scale_y = 110.57
        point_xy = (point[0] * scale_x, point[1] * scale_y)
        start_xy = (start[0] * scale_x, start[1] * scale_y)
        end_xy = (end[0] * scale_x, end[1] * scale_y)
        dx = end_xy[0] - start_xy[0]
        dy = end_xy[1] - start_xy[1]
        length_squared = dx * dx + dy * dy
        if length_squared == 0:
            return math.dist(point_xy, start_xy)
        projection = ((point_xy[0] - start_xy[0]) * dx + (point_xy[1] - start_xy[1]) * dy) / length_squared
        projection = max(0, min(1, projection))
        closest = (start_xy[0] + projection * dx, start_xy[1] + projection * dy)
        return math.dist(point_xy, closest)

    @staticmethod
    def _normalize_category(category: str) -> str:
        normalized = category.strip().lower()
        if normalized == "attractions":
            normalized = "attraction"
        if normalized == "cafes":
            normalized = "coffee"
        if normalized not in GooglePlacesProvider._CATEGORY_QUERIES:
            raise ValueError(f"Unsupported POI category: {category}")
        return normalized