import inspect

from ...core.errors import APIError
from ...core.fixture_repository import FixtureRepository
from ...models.contracts import (
    AssistantIntent,
    BorderCrossing,
    Coordinates,
    RouteAlert,
    RouteRequirement,
    RouteResponse,
    TripStats,
)
from .ports import (
    GeocodedPlace,
    InvalidDestinationError,
    ChargingProvider,
    JourneyProviderError,
    RoutingProvider,
    RoutingProviderError,
)
from .deterministic import enrich_partner, select_charger
from .country_rules import derive_requirements, detect_border_crossings


DEFAULT_ORIGIN = "Vienna, Austria"


class RouteService:
    def __init__(
        self,
        provider: RoutingProvider,
        fixture_repository: FixtureRepository,
        origin: str = DEFAULT_ORIGIN,
        charging_provider: ChargingProvider | None = None,
        safety_buffer_km: float = 10,
    ) -> None:
        self._provider = provider
        self._fixture_repository = fixture_repository
        self._origin = origin
        self._charging_provider = charging_provider
        self._safety_buffer_km = safety_buffer_km

    async def plan(self, intent: AssistantIntent) -> RouteResponse:
        try:
            origin = await self._provider.geocode(self._origin)
            destination = await self._provider.geocode(intent.destination)
            provider_route = await self._provider.route(
                origin, destination, intent.priority
            )
        except InvalidDestinationError as error:
            raise APIError(
                400, "INVALID_DESTINATION", "The destination could not be found."
            ) from error
        except (RoutingProviderError, OSError) as error:
            raise APIError(
                503, "ROUTING_UNAVAILABLE", "The routing service is unavailable."
            ) from error

        if (
            provider_route.distance_meters < 0
            or provider_route.duration_seconds < 0
            or len(provider_route.geometry) < 2
        ):
            raise APIError(503, "INVALID_ROUTE", "The routing service returned invalid data.")

        distance_km = round(provider_route.distance_meters / 1000, 2)
        driving_minutes = round(provider_route.duration_seconds / 60, 1)
        stops = []
        total_minutes = driving_minutes
        if self._charging_provider and distance_km > self._safe_distance_km():
            try:
                candidates = await self._charging_provider.search_charging(
                    provider_route, self._safe_distance_km()
                )
            except (JourneyProviderError, OSError) as error:
                raise APIError(
                    503,
                    "CHARGING_UNAVAILABLE",
                    "The charging service is unavailable.",
                ) from error
            candidate = select_charger(candidates, self._safe_distance_km())
            if candidate is None:
                raise APIError(
                    422,
                    "NO_SUITABLE_CHARGER",
                    "No suitable charging stop was found for this route.",
                )
            if candidate is not None:
                stop = enrich_partner(
                    candidate.stop, self._fixture_repository.fixtures.partners
                ).model_copy(update={"mandatory": True})
                stops.append(stop)
                if not self._supports_waypoints():
                    raise APIError(
                        503,
                        "ROUTING_UNAVAILABLE",
                        "The routing service cannot route through a charging stop.",
                    )
                waypoint = GeocodedPlace(
                    stop.name,
                    Coordinates(lng=stop.coords[0], lat=stop.coords[1]),
                )
                try:
                    provider_route = await self._provider.route(
                        origin, destination, intent.priority, (waypoint,)
                    )
                except (RoutingProviderError, OSError) as error:
                    raise APIError(
                        503,
                        "ROUTING_UNAVAILABLE",
                        "The routing service is unavailable.",
                    ) from error
                distance_km = round(provider_route.distance_meters / 1000, 2)
                driving_minutes = round(provider_route.duration_seconds / 60, 1)
                total_minutes = round(driving_minutes + stop.detour_minutes, 1)

        alerts = self._range_alert(distance_km) if not stops else []
        border_crossings = [
            BorderCrossing(from_country=source, to_country=target)
            for source, target in provider_route.border_crossings
        ] or detect_border_crossings(provider_route.countries)
        requirements = derive_requirements(provider_route.countries)

        return RouteResponse(
            origin=origin.display_name,
            destination=destination.display_name,
            stats=TripStats(
                total_distance_km=distance_km,
                total_duration_minutes=total_minutes,
                driving_duration_minutes=driving_minutes,
            ),
            geometry=list(provider_route.geometry),
            stops=stops,
            alerts=alerts,
            border_crossings=border_crossings,
            route_requirements=requirements,
        )

    def _safe_distance_km(self) -> float:
        return max(
            0,
            self._fixture_repository.fixtures.telemetry.estimated_range_km
            - self._safety_buffer_km,
        )

    def _supports_waypoints(self) -> bool:
        return "waypoints" in inspect.signature(self._provider.route).parameters


    def _range_alert(self, distance_km: float) -> list[RouteAlert]:
        vehicle_range = self._fixture_repository.fixtures.telemetry.estimated_range_km
        if distance_km <= vehicle_range:
            return []
        return [
            RouteAlert(
                type="VEHICLE",
                severity="WARNING",
                message=(
                    f"Vehicle estimated range is {vehicle_range:g} km; "
                    f"route distance is {distance_km:g} km. Charging may be required."
                ),
            )
        ]