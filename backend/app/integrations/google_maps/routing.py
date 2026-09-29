import logging
import re
from time import monotonic

import httpx

from ...models.contracts import Coordinates, RoutePriority
from ...core.async_cache import AsyncTTLCache
from ...services.trip.ports import (
    GeocodedPlace,
    InvalidDestinationError,
    ProviderRoute,
    ProviderToll,
    RoutingProviderError,
)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
_DURATION_PATTERN = re.compile(r"^(?P<seconds>[0-9]+(?:\.[0-9]+)?)s$")
LOGGER = logging.getLogger(__name__)
SCENIC_HIGHWAY_CORRIDOR_MARKERS = (
    "grossglockner",
    "alpine road",
    "dolomites",
    "trollstigen",
)


class GoogleMapsRoutingProvider:
    def __init__(self, api_key: str | None, timeout_seconds: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._geocode_cache = AsyncTTLCache[str, GeocodedPlace](3600, 256)
        self._route_cache = AsyncTTLCache[tuple[object, ...], ProviderRoute](300, 256)

    async def geocode(self, place: str) -> GeocodedPlace:
        key = place.strip().casefold()
        return await self._geocode_cache.get_or_create(
            key, lambda: self._geocode_uncached(place)
        )

    async def _geocode_uncached(self, place: str) -> GeocodedPlace:
        if not self._api_key:
            raise RoutingProviderError("GOOGLE_SERVER_API_KEY is not configured")

        started_at = monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    GEOCODE_URL,
                    params={"address": place, "key": self._api_key},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, AttributeError, ValueError, TypeError) as error:
            LOGGER.warning(
                "geocode_ms=%d place=%s error=%s",
                round((monotonic() - started_at) * 1000),
                place,
                type(error).__name__,
            )
            raise RoutingProviderError("Google geocoding request failed") from error

        results = payload.get("results") or []
        if not results:
            raise InvalidDestinationError(place)

        try:
            result = results[0]
            location = result["geometry"]["location"]
            coordinates = Coordinates(lng=float(location["lng"]), lat=float(location["lat"]))
        except (KeyError, TypeError, ValueError) as error:
            raise RoutingProviderError("Google geocoding response was invalid") from error

        latency_ms = round((monotonic() - started_at) * 1000)
        LOGGER.info("geocode_ms=%d place=%s", latency_ms, place)
        return GeocodedPlace(
            display_name=result.get("formatted_address", place),
            coordinates=coordinates,
        )

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
        waypoints: tuple[GeocodedPlace, ...] | None = None,
    ) -> ProviderRoute:
        key = (
            round(origin.coordinates.lng, 6),
            round(origin.coordinates.lat, 6),
            round(destination.coordinates.lng, 6),
            round(destination.coordinates.lat, 6),
            priority,
            tuple(
                (
                    round(waypoint.coordinates.lng, 6),
                    round(waypoint.coordinates.lat, 6),
                )
                for waypoint in (waypoints or ())
            ),
        )
        return await self._route_cache.get_or_create(
            key, lambda: self._route_uncached(origin, destination, priority, waypoints)
        )

    async def _route_uncached(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
        waypoints: tuple[GeocodedPlace, ...] | None = None,
    ) -> ProviderRoute:
        if not self._api_key:
            raise RoutingProviderError("GOOGLE_SERVER_API_KEY is not configured")

        started_at = monotonic()
        request = {
            "origin": {"location": {"latLng": self._lat_lng(origin)}},
            "destination": {"location": {"latLng": self._lat_lng(destination)}},
            "travelMode": "DRIVE",
            "routingPreference": self._routing_preference(priority),
            "polylineQuality": "HIGH_QUALITY",
            "polylineEncoding": "GEO_JSON_LINESTRING",
            "units": "METRIC",
            "languageCode": "en-US",
            "extraComputations": ["TOLLS"],
        }
        if priority == RoutePriority.SCENIC and not self._known_scenic_highway_corridor(
            destination.display_name
        ):
            request["routeModifiers"] = {"avoidHighways": True}
        if waypoints:
            request["intermediates"] = [
                {"location": {"latLng": self._lat_lng(waypoint)}}
                for waypoint in waypoints
            ]
        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": (
                "routes.distanceMeters,routes.duration,"
                "routes.polyline.geoJsonLinestring,routes.travelAdvisory.tollInfo"
            ),
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(ROUTES_URL, json=request, headers=headers)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, AttributeError, ValueError, TypeError) as error:
            LOGGER.warning(
                "route_provider_ms=%d error=%s",
                round((monotonic() - started_at) * 1000),
                type(error).__name__,
            )
            raise RoutingProviderError("Google route request failed") from error

        try:
            route = (payload.get("routes") or [])[0]
            duration = _DURATION_PATTERN.fullmatch(route["duration"])
            if duration is None:
                raise ValueError("Invalid Google duration")
            geometry = tuple(
                (float(point[0]), float(point[1]))
                for point in route["polyline"]["geoJsonLinestring"]["coordinates"]
            )
            if len(geometry) < 2:
                raise ValueError("Google route geometry is incomplete")
            tolls = tuple(
                ProviderToll(
                    amount=float(price.get("units", 0))
                    + float(price.get("nanos", 0)) / 1_000_000_000,
                    currency=str(price["currencyCode"]),
                )
                for price in (route.get("travelAdvisory", {}).get("tollInfo", {})
                              .get("estimatedPrice", []) or [])
            )
            provider_route = ProviderRoute(
                distance_meters=float(route["distanceMeters"]),
                duration_seconds=float(duration.group("seconds")),
                geometry=geometry,
                tolls=tolls,
            )
            LOGGER.info(
                "route_provider_ms=%d distance_meters=%s duration_seconds=%s",
                round((monotonic() - started_at) * 1000),
                provider_route.distance_meters,
                provider_route.duration_seconds,
            )
            return provider_route
        except (IndexError, KeyError, TypeError, ValueError) as error:
            LOGGER.warning(
                "route_provider_ms=%d error=%s",
                round((monotonic() - started_at) * 1000),
                type(error).__name__,
            )
            raise RoutingProviderError("Google route response was invalid") from error

    @staticmethod
    def _lat_lng(place: GeocodedPlace) -> dict[str, float]:
        return {
            "latitude": place.coordinates.lat,
            "longitude": place.coordinates.lng,
        }

    @staticmethod
    def _routing_preference(priority: RoutePriority) -> str:
        if priority == RoutePriority.FASTEST:
            return "TRAFFIC_AWARE_OPTIMAL"
        if priority == RoutePriority.SCENIC:
            return "TRAFFIC_AWARE"
        return "TRAFFIC_AWARE"

    @staticmethod
    def _known_scenic_highway_corridor(destination_name: str) -> bool:
        normalized = destination_name.casefold()
        return any(marker in normalized for marker in SCENIC_HIGHWAY_CORRIDOR_MARKERS)
