from ...core.errors import APIError
from ...core.fixture_repository import FixtureRepository
from ...models.contracts import AssistantIntent, RouteAlert, RouteResponse, TripStats
from .ports import (
    GeocodedPlace,
    InvalidDestinationError,
    RoutingProvider,
    RoutingProviderError,
)


DEFAULT_ORIGIN = "Vienna, Austria"


class RouteService:
    def __init__(
        self,
        provider: RoutingProvider,
        fixture_repository: FixtureRepository,
        origin: str = DEFAULT_ORIGIN,
    ) -> None:
        self._provider = provider
        self._fixture_repository = fixture_repository
        self._origin = origin

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

        if provider_route.distance_meters < 0 or provider_route.duration_seconds < 0:
            raise APIError(503, "INVALID_ROUTE", "The routing service returned invalid data.")

        distance_km = round(provider_route.distance_meters / 1000, 2)
        duration_minutes = round(provider_route.duration_seconds / 60, 1)
        alerts = self._range_alert(distance_km)

        return RouteResponse(
            origin=origin.display_name,
            destination=destination.display_name,
            stats=TripStats(
                total_distance_km=distance_km,
                total_duration_minutes=duration_minutes,
            ),
            geometry=list(provider_route.geometry),
            alerts=alerts,
        )

    def _range_alert(self, distance_km: float) -> list[RouteAlert]:
        vehicle_range = self._fixture_repository.fixtures.telemetry.estimated_range_km
        if distance_km <= vehicle_range:
            return []
        return [
            RouteAlert(
                type="VEHICLE",
                severity="WARNING",
                message=(
                    f"Your car has an estimated range of {vehicle_range:g} km and "
                    "cannot cover this distance. Should I add a charging stop for you?"
                ),
            )
        ]