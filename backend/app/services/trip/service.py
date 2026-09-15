import inspect
from uuid import uuid4

from ...core.errors import APIError
from ...core.fixture_repository import FixtureRepository
from ...core.route_country_rules import (
    derive_route_requirements,
    detect_border_crossings as detect_rule_crossings,
    load_route_country_rules,
)
from ...integrations.places.provider import LocalPlacesProvider
from ...models.contracts import (
    AssistantIntent,
    BorderCrossing,
    Coordinates,
    RouteAlert,
    RouteRequirement,
    RouteResponse,
    StopPinpoint,
    TripStats,
)
from .country_rules import derive_requirements, detect_border_crossings
from .deterministic import enrich_partner, select_charger
from .fixture_providers import FixtureChargingProvider
from .ports import (
    ChargingProvider,
    GeocodedPlace,
    InvalidDestinationError,
    JourneyProviderError,
    RoutingProvider,
    RoutingProviderError,
    JourneyProviderError,
)


DEFAULT_ORIGIN = "Vienna, Austria"


class RouteService:
    def __init__(
        self,
        provider: RoutingProvider,
        fixture_repository: FixtureRepository,
        origin: str = DEFAULT_ORIGIN,
        charging_provider: ChargingProvider | None = None,
        safety_buffer_km: float = 10,
        places_provider: LocalPlacesProvider | None = None,
    ) -> None:
        self._provider = provider
        self._fixture_repository = fixture_repository
        self._origin = origin
        self._charging_provider = charging_provider
        self._safety_buffer_km = safety_buffer_km
        self._places_provider = places_provider or LocalPlacesProvider(
            fixture_repository
        )
        self._active_provider_route = None
        self._active_route_id: str | None = None
        self._active_search_id: str | None = None
        self._active_origin: GeocodedPlace | None = None
        self._active_destination: GeocodedPlace | None = None
        self._active_priority = None
        self._active_stops: list[StopPinpoint] = []
        self._active_search_results: dict[str, StopPinpoint] = {}

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

        self._validate_route(provider_route)
        initial_distance_km = round(provider_route.distance_meters / 1000, 2)
        safe_distance_km = self._safe_distance_km()
        stops: list[StopPinpoint] = []

        if initial_distance_km > safe_distance_km:
            charging_provider = self._charging_provider or FixtureChargingProvider(
                self._fixture_repository.fixtures.partners
            )
            try:
                candidates = await charging_provider.search_charging(
                    provider_route, safe_distance_km
                )
            except (JourneyProviderError, OSError) as error:
                raise APIError(
                    503,
                    "CHARGING_UNAVAILABLE",
                    "The charging service is unavailable.",
                ) from error

            candidate = select_charger(candidates, safe_distance_km)
            if candidate is None:
                raise APIError(
                    422,
                    "NO_SUITABLE_CHARGER",
                    "No suitable charging stop was found for this route.",
                )

            charging_stop = enrich_partner(
                candidate.stop, self._fixture_repository.fixtures.partners
            ).model_copy(update={"mandatory": True})
            charging_stop = charging_stop.model_copy(
                update={
                    "charging_duration_minutes": candidate.charging_duration_minutes
                    or charging_stop.charging_duration_minutes
                }
            )
            stops.append(charging_stop)

            if not self._supports_waypoints():
                raise APIError(
                    503,
                    "ROUTING_UNAVAILABLE",
                    "The routing service cannot route through a charging stop.",
                )

            waypoint = GeocodedPlace(
                charging_stop.name,
                Coordinates(
                    lng=charging_stop.coords[0], lat=charging_stop.coords[1]
                ),
            )
            try:
                provider_route = await self._provider.route(
                    origin, destination, intent.priority, (waypoint,)
                )
            except (RoutingProviderError, OSError) as error:
                raise APIError(
                    503, "ROUTING_UNAVAILABLE", "The routing service is unavailable."
                ) from error
            self._validate_route(provider_route)

        route_response = self._build_route_response(
            provider_route, origin, destination, stops
        )
        self._active_provider_route = provider_route
        self._active_route_id = uuid4().hex
        self._active_search_id = None
        self._active_origin = origin
        self._active_destination = destination
        self._active_priority = intent.priority
        self._active_stops = list(stops)
        self._active_search_results = {}
        return route_response

    async def search_route_poi(
        self,
        category: str,
        location: str | None = None,
        preference: str | None = None,
    ) -> list[StopPinpoint]:
        try:
            results = await self._places_provider.search(
                category,
                location,
                preference,
                route=self._active_provider_route,
            )
            self._active_search_id = uuid4().hex
            self._active_search_results = {result.id: result for result in results}
            return results
        except ValueError as error:
            raise APIError(
                400,
                "INVALID_POI_CATEGORY",
                "The requested POI category is not supported.",
            ) from error
        except JourneyProviderError as error:
            raise APIError(
                503,
                "POI_UNAVAILABLE",
                "The place search service is unavailable.",
            ) from error

    async def reroute_through_poi(
        self,
        poi_id: str,
        route_id: str,
        search_id: str,
        coords: tuple[float, float] | None = None,
        priority=None,
    ) -> RouteResponse:
        if (
            self._active_provider_route is None
            or self._active_origin is None
            or self._active_destination is None
            or route_id != self._active_route_id
            or search_id != self._active_search_id
        ):
            raise APIError(409, "STALE_POI", "The selected place is no longer current.")
        stop = self._active_search_results.get(poi_id)
        if stop is None:
            raise APIError(409, "STALE_POI", "The selected place is no longer current.")
        if coords is not None and self._invalid_coordinates(coords):
            raise APIError(422, "INVALID_POI_COORDINATES", "The selected place coordinates are invalid.")
        if coords is not None and any(
            abs(coords[index] - stop.coords[index]) > 0.01 for index in (0, 1)
        ):
            raise APIError(422, "INVALID_POI_COORDINATES", "The selected place coordinates are invalid.")
        if not self._supports_waypoints():
            raise APIError(503, "ROUTING_UNAVAILABLE", "The routing service cannot route through a place.")

        selected_priority = priority or self._active_priority
        waypoints = tuple(
            GeocodedPlace(item.name, Coordinates(lng=item.coords[0], lat=item.coords[1]))
            for item in (*self._active_stops, stop)
        )
        try:
            provider_route = await self._provider.route(
                self._active_origin,
                self._active_destination,
                selected_priority,
                waypoints,
            )
            self._validate_route(provider_route)
        except (RoutingProviderError, OSError) as error:
            raise APIError(
                503, "ROUTING_UNAVAILABLE", "The routing service is unavailable."
            ) from error

        route_response = self._build_route_response(
            provider_route,
            self._active_origin,
            self._active_destination,
            [*self._active_stops, stop],
        )
        self._active_provider_route = provider_route
        self._active_priority = selected_priority
        self._active_stops = [*self._active_stops, stop]
        self._active_route_id = uuid4().hex
        self._active_search_id = None
        self._active_search_results = {}
        return route_response

    @staticmethod
    def _invalid_coordinates(coords: tuple[float, float]) -> bool:
        return (
            len(coords) != 2
            or not all(isinstance(value, (int, float)) for value in coords)
            or not -180 <= coords[0] <= 180
            or not -90 <= coords[1] <= 90
        )

    def _build_route_response(
        self,
        provider_route: object,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        stops: list[StopPinpoint],
    ) -> RouteResponse:
        distance_km = round(provider_route.distance_meters / 1000, 2)
        driving_minutes = round(provider_route.duration_seconds / 60, 1)
        total_minutes = round(
            driving_minutes
            + sum(
                stop.detour_minutes + stop.charging_duration_minutes
                for stop in stops
            ),
            1,
        )
        border_crossings, route_requirements = self._route_facts(
            provider_route, origin.display_name, destination.display_name
        )
        if provider_route.tolls and not any(
            requirement.kind == "toll" for requirement in route_requirements
        ):
            route_requirements.append(
                RouteRequirement(
                    id="google-route-toll",
                    name="Road toll applies",
                    country="",
                    kind="toll",
                )
            )
        total_price_eur = sum(
            toll.amount for toll in provider_route.tolls if toll.currency == "EUR"
        )
        return RouteResponse(
            origin=origin.display_name,
            destination=destination.display_name,
            stats=TripStats(
                total_distance_km=distance_km,
                driving_duration_minutes=driving_minutes,
                total_duration_minutes=total_minutes,
                total_price_eur=round(total_price_eur, 2),
            ),
            geometry=list(provider_route.geometry),
            stops=stops,
            charging_stop=next(
                (stop for stop in stops if stop.mandatory and stop.category == "charging"),
                None,
            ),
            alerts=self._range_alert(distance_km) if not stops else [],
            border_crossings=border_crossings,
            route_requirements=route_requirements,
        )

    def _safe_distance_km(self) -> float:
        return max(
            0,
            self._fixture_repository.fixtures.telemetry.estimated_range_km
            - self._safety_buffer_km,
        )

    def _supports_waypoints(self) -> bool:
        return "waypoints" in inspect.signature(self._provider.route).parameters

    @staticmethod
    def _validate_route(provider_route: object) -> None:
        if (
            provider_route.distance_meters < 0
            or provider_route.duration_seconds < 0
            or len(provider_route.geometry) < 2
        ):
            raise APIError(
                503, "INVALID_ROUTE", "The routing service returned invalid data."
            )

    def _route_facts(
        self, provider_route: object, origin: str, destination: str
    ) -> tuple[list[BorderCrossing], list[RouteRequirement]]:
        if provider_route.countries:
            return (
                detect_border_crossings(provider_route.countries),
                derive_requirements(provider_route.countries),
            )

        rules = load_route_country_rules()
        crossing_ids = detect_rule_crossings(origin, destination, rules)
        crossings: list[BorderCrossing] = []
        for crossing in rules.get("border_crossings", []):
            if crossing.get("id") in crossing_ids:
                crossings.append(
                    BorderCrossing(
                        from_country=crossing["from_country"],
                        to_country=crossing["to_country"],
                    )
                )

        requirements: list[RouteRequirement] = []
        for name in derive_route_requirements(crossing_ids, rules):
            requirements.append(
                RouteRequirement(
                    id=name.casefold().replace(" ", "-"),
                    name=name,
                    country="HU" if "Hungarian" in name else "",
                    kind="vignette" if "vignette" in name.casefold() else "toll",
                )
            )
        return crossings, requirements

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
