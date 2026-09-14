import re

import httpx

from ...models.contracts import Coordinates, RoutePriority
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


class GoogleMapsRoutingProvider:
    def __init__(self, api_key: str | None, timeout_seconds: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def geocode(self, place: str) -> GeocodedPlace:
        if not self._api_key:
            raise RoutingProviderError("GOOGLE_SERVER_API_KEY is not configured")

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    GEOCODE_URL,
                    params={"address": place, "key": self._api_key},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as error:
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
        if not self._api_key:
            raise RoutingProviderError("GOOGLE_SERVER_API_KEY is not configured")

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
        except (httpx.HTTPError, ValueError, TypeError) as error:
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
            return ProviderRoute(
                distance_meters=float(route["distanceMeters"]),
                duration_seconds=float(duration.group("seconds")),
                geometry=geometry,
                tolls=tolls,
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise RoutingProviderError("Google route response was invalid") from error

    @staticmethod
    def _lat_lng(place: GeocodedPlace) -> dict[str, float]:
        return {
            "latitude": place.coordinates.lat,
            "longitude": place.coordinates.lng,
        }

    @staticmethod
    def _routing_preference(priority: RoutePriority) -> str:
        return "TRAFFIC_AWARE_OPTIMAL" if priority == RoutePriority.FASTEST else "TRAFFIC_AWARE"
