from ...core.errors import APIError
from ...core.fixture_repository import FixtureRepository
from ...models.contracts import (
    AssistantIntent,
    RouteAlert,
    RouteResponse,
    StopPinpoint,
    TripStats,
)
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

        if (
            provider_route.distance_meters < 0
            or provider_route.duration_seconds < 0
            or len(provider_route.geometry) < 2
        ):
            raise APIError(503, "INVALID_ROUTE", "The routing service returned invalid data.")

        distance_km = round(provider_route.distance_meters / 1000, 2)
        driving_duration_minutes = round(provider_route.duration_seconds / 60, 1)
        alerts = self._range_alert(distance_km)
        charging_stop = self._build_charging_stop(distance_km)
        border_crossings = self._detect_border_crossings(origin, destination)
        route_requirements = self._route_requirements(border_crossings, destination)

        return RouteResponse(
            origin=origin.display_name,
            destination=destination.display_name,
            stats=TripStats(
                total_distance_km=distance_km,
                driving_duration_minutes=driving_duration_minutes,
                total_duration_minutes=driving_duration_minutes,
            ),
            geometry=list(provider_route.geometry),
            alerts=alerts,
            charging_stop=charging_stop,
            border_crossings=border_crossings,
            route_requirements=route_requirements,
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
                    f"Vehicle estimated range is {vehicle_range:g} km; "
                    f"route distance is {distance_km:g} km. Charging may be required."
                ),
            )
        ]

    def _build_charging_stop(self, distance_km: float) -> StopPinpoint | None:
        vehicle_range = self._fixture_repository.fixtures.telemetry.estimated_range_km
        if distance_km <= vehicle_range:
            return None

        charging_candidate = None
        for partner in self._fixture_repository.fixtures.partners:
            if partner.category != "charging":
                continue
            if charging_candidate is None:
                charging_candidate = partner
                continue
            if partner.detour_minutes < charging_candidate.detour_minutes:
                charging_candidate = partner
                continue
            if (
                partner.detour_minutes == charging_candidate.detour_minutes
                and (partner.rating or 0) > (charging_candidate.rating or 0)
            ):
                charging_candidate = partner

        if charging_candidate is None:
            return None

        partner_benefit = None
        tag = (charging_candidate.tag or "").lower()
        if any(keyword in tag for keyword in ("discount", "rate", "benefit")):
            partner_benefit = charging_candidate.tag

        return StopPinpoint(
            id=charging_candidate.id,
            name=charging_candidate.name,
            category="charging",
            coords=(charging_candidate.coords[0], charging_candidate.coords[1]),
            rating=charging_candidate.rating,
            tag=charging_candidate.tag,
            detour_minutes=float(charging_candidate.detour_minutes),
            partner_benefit=partner_benefit,
        )

    def _route_requirements(
        self, border_crossings: list[str], destination: GeocodedPlace
    ) -> list[str]:
        requirements: list[str] = []
        if border_crossings and (
            "Hungary" in destination.display_name or "Budapest" in destination.display_name
        ):
            requirements.append("Hungarian motorway vignette")
        return requirements

    def _detect_border_crossings(
        self, origin: GeocodedPlace, destination: GeocodedPlace
    ) -> list[str]:
        origin_display = origin.display_name
        destination_display = destination.display_name

        if (
            "Austria" in origin_display
            and ("Hungary" in destination_display or "Budapest" in destination_display)
        ):
            return ["Austria-Hungary"]
        return []