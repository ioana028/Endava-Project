from __future__ import annotations

import logging
import math
from time import monotonic

import httpx

from ...models.contracts import StopPinpoint
from ...services.trip.deterministic import distance_to_route_km, route_progress_km
from ...services.trip.ports import ChargingCandidate, JourneyProviderError, ProviderRoute


PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
LOGGER = logging.getLogger(__name__)


class GooglePlacesProvider:
    _CATEGORY_QUERIES = {
        "hotel": "hotels",
        "restaurant": "restaurants",
        "food": "restaurants and places to eat",
        "attraction": "tourist attractions and interesting places to see",
        "charging": "electric vehicle charging stations",
        "coffee": "coffee shops and cafes",
        "rest": "rest areas and service areas",
        "toilets": "public toilets and restrooms",
        "fuel": "fuel stations and petrol stations",
        "service": "vehicle service and repair shops",
    }

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 10.0,
        search_radius_meters: float = 7500,
        nearby_search_radius_meters: float = 500,
        sample_interval_km: float = 50,
        max_search_points: int = 8,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._search_radius_meters = float(search_radius_meters)
        self._nearby_search_radius_meters = float(nearby_search_radius_meters)
        self._sample_interval_km = sample_interval_km
        self._max_search_points = max(2, max_search_points)

    async def search(
        self,
        category: str,
        location: str | None = None,
        preference: str | None = None,
        route: ProviderRoute | None = None,
        near_coords: tuple[float, float] | None = None,
    ) -> list[StopPinpoint]:
        normalized = self._normalize_category(category)
        if not self._api_key:
            raise JourneyProviderError("Google Places is not configured")
        if route is None or len(route.geometry) < 2:
            return []

        query = self._CATEGORY_QUERIES[normalized]
        if preference:
            query = f"{preference} {query}"
        radius = (
            self._search_radius_meters
            if location == "route"
            else self._nearby_search_radius_meters
            if location == "stop"
            else max(self._search_radius_meters, 2_500)
        )
        results: dict[str, StopPinpoint] = {}
        request_count = 0
        started_at = monotonic()

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                for longitude, latitude in self._search_points(
                    route, location, near_coords
                ):
                    request_count += 1
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
                                "places.rating,places.editorialSummary,places.formattedAddress,"
                                "places.evChargeOptions"
                            ),
                        },
                    )
                    response.raise_for_status()
                    for place in response.json().get("places", []):
                        stop = self._to_stop(place, normalized, route)
                        if stop is not None:
                            results[stop.id] = stop
        except (httpx.HTTPError, AttributeError, ValueError, TypeError) as error:
            LOGGER.warning(
                "google_places_search_failed category=%s samples=%d failure_code=%s latency_ms=%d",
                normalized,
                request_count,
                self._failure_code(error),
                round((monotonic() - started_at) * 1000),
            )
            raise JourneyProviderError("Google Places search failed") from error

        LOGGER.info(
            "google_places_search category=%s location=%s samples=%d results=%d latency_ms=%d",
            normalized,
            location or "route",
            request_count,
            len(results),
            round((monotonic() - started_at) * 1000),
        )

        result_limit = 50 if normalized == "charging" else 10
        return sorted(
            results.values(),
            key=lambda stop: (stop.detour_minutes, -(stop.rating or 0), stop.name),
        )[:result_limit]

    async def search_charging(
        self, route: ProviderRoute, max_distance_km: float
    ) -> tuple[ChargingCandidate, ...]:
        stops = await self.search("charging", location="route", route=route)
        return tuple(
            ChargingCandidate(
                stop=stop,
                distance_from_route_km=distance_to_route_km(
                    stop.coords, tuple(route.geometry)
                ),
                distance_from_origin_km=route_progress_km(
                    stop.coords, tuple(route.geometry)
                ),
                charging_power_kw=stop.charging_power_kw,
                charging_duration_minutes=stop.charging_duration_minutes,
            )
            for stop in stops
            if route_progress_km(stop.coords, tuple(route.geometry)) <= max_distance_km
        )

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
        corridor_radius_km = max(self._search_radius_meters / 1000, 7.5)
        if route_distance_km > corridor_radius_km:
            return None
        rating = place.get("rating")
        summary = place.get("editorialSummary") or {}
        address = place.get("formattedAddress")
        types = tuple(str(item).casefold() for item in (place.get("types") or ()))
        if not self._supports_requested_category(category, types):
            return None
        factual_types = self._factual_types(types)
        charging_power_kw = self._charging_power_kw(place)
        tag = str(summary.get("text") or address or "Google Maps place")
        if factual_types:
            tag = f"{tag} ({', '.join(factual_types)})"
        return StopPinpoint(
            id=place_id,
            name=name,
            category=category,
            coords=coords,
            rating=float(rating) if rating is not None else None,
            tag=tag,
            amenities=factual_types,
            charging_power_kw=charging_power_kw,
            detour_minutes=round(route_distance_km, 1),
        )

    @staticmethod
    def _charging_power_kw(place: dict[str, object]) -> float | None:
        options = place.get("evChargeOptions") or {}
        connectors = options.get("connectorAggregation", []) if isinstance(options, dict) else []
        rates = [
            float(item["maxChargeRateKw"])
            for item in connectors
            if isinstance(item, dict) and item.get("maxChargeRateKw") is not None
        ]
        return max(rates) if rates else None

    def _search_points(
        self,
        route: ProviderRoute,
        location: str | None,
        near_coords: tuple[float, float] | None = None,
    ) -> tuple[tuple[float, float], ...]:
        if location == "stop" and near_coords is not None:
            return (near_coords,)
        geometry = route.geometry
        if location == "destination":
            return (geometry[-1],)
        return self._distance_samples(geometry)

    def _distance_samples(
        self, geometry: tuple[tuple[float, float], ...]
    ) -> tuple[tuple[float, float], ...]:
        if len(geometry) < 2:
            return geometry
        total_km = sum(
            self._haversine_km(start, end) for start, end in zip(geometry, geometry[1:])
        )
        interval_km = max(self._sample_interval_km, 0.1)
        sample_count = min(
            self._max_search_points,
            max(2, math.ceil(total_km / interval_km) + 1),
        )
        targets = [
            index * total_km / (sample_count - 1)
            for index in range(sample_count)
        ]
        samples: list[tuple[float, float]] = []
        segment_start = 0.0
        segment_index = 0
        for target in targets:
            while segment_index < len(geometry) - 2:
                segment_length = self._haversine_km(
                    geometry[segment_index], geometry[segment_index + 1]
                )
                if segment_start + segment_length >= target:
                    break
                segment_start += segment_length
                segment_index += 1
            start = geometry[segment_index]
            end = geometry[segment_index + 1]
            segment_length = self._haversine_km(start, end)
            fraction = (
                0
                if segment_length == 0
                else (target - segment_start) / segment_length
            )
            fraction = max(0, min(1, fraction))
            samples.append(
                (
                    start[0] + (end[0] - start[0]) * fraction,
                    start[1] + (end[1] - start[1]) * fraction,
                )
            )
        return tuple(dict.fromkeys(samples))

    @staticmethod
    def _haversine_km(
        first: tuple[float, float], second: tuple[float, float]
    ) -> float:
        longitude_one, latitude_one = map(math.radians, first)
        longitude_two, latitude_two = map(math.radians, second)
        delta_longitude = longitude_two - longitude_one
        delta_latitude = latitude_two - latitude_one
        value = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(latitude_one)
            * math.cos(latitude_two)
            * math.sin(delta_longitude / 2) ** 2
        )
        return 6371 * 2 * math.asin(math.sqrt(value))

    @staticmethod
    def _factual_types(types: tuple[str, ...]) -> tuple[str, ...]:
        labels = (
            ("gas_station", "fuel station"),
            ("electric_vehicle_charging_station", "charging"),
            ("cafe", "cafe"),
            ("coffee_shop", "coffee"),
            ("convenience_store", "convenience store"),
            ("rest_area", "rest area"),
            ("toilet", "toilets"),
        )
        return tuple(label for provider_type, label in labels if provider_type in types)

    @staticmethod
    def _supports_requested_category(category: str, types: tuple[str, ...]) -> bool:
        if "gas_station" not in types:
            return True
        supporting_types = {
            "cafe",
            "coffee_shop",
            "convenience_store",
            "food",
            "restaurant",
            "rest_area",
            "service_area",
            "toilet",
        }
        if category == "coffee":
            return bool(supporting_types.intersection(types))
        if category in {"rest", "toilets"}:
            return bool(supporting_types.intersection(types))
        return True

    @staticmethod
    def _failure_code(error: Exception) -> str:
        if isinstance(error, httpx.TimeoutException):
            return "timeout"
        if isinstance(error, httpx.HTTPStatusError):
            return f"http_{error.response.status_code}"
        if isinstance(error, (ValueError, TypeError, AttributeError)):
            return "malformed_response"
        return "request_failed"

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
        if normalized in {"toilet", "toilets"}:
            normalized = "toilets"
        if normalized in {"fuel", "fuels", "petrol", "gas"}:
            normalized = "fuel"
        if normalized not in GooglePlacesProvider._CATEGORY_QUERIES:
            raise ValueError(f"Unsupported POI category: {category}")
        return normalized