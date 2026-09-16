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
from .deterministic import (
    POI_COORDINATE_TOLERANCE,
    enrich_partner,
    estimate_charging_duration_minutes,
    route_progress_km,
    select_stop_amenities,
    select_charger,
    select_route_stops,
)
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

    @property
    def active_route_id(self) -> str | None:
        return self._active_route_id

    @property
    def active_search_id(self) -> str | None:
        return self._active_search_id

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
        reachable_distance_km = self._fixture_repository.fixtures.telemetry.estimated_range_km
        stops: list[StopPinpoint] = []

        if initial_distance_km > safe_distance_km:
            charging_provider = self._charging_provider or FixtureChargingProvider(
                self._fixture_repository.fixtures.partners
            )
            try:
                candidates = await charging_provider.search_charging(
                    provider_route, reachable_distance_km
                )
            except (JourneyProviderError, OSError) as error:
                raise APIError(
                    503,
                    "CHARGING_UNAVAILABLE",
                    "The charging service is unavailable.",
                ) from error

            enriched_candidates = tuple(
                candidate.__class__(
                    stop=enrich_partner(candidate.stop, self._fixture_repository.fixtures.partners),
                    compatible=candidate.compatible,
                    available=candidate.available,
                    distance_from_route_km=candidate.distance_from_route_km,
                    distance_from_origin_km=candidate.distance_from_origin_km,
                    charging_power_kw=candidate.charging_power_kw,
                    charging_duration_minutes=candidate.charging_duration_minutes,
                )
                for candidate in candidates
            )
            candidate = select_charger(enriched_candidates, reachable_distance_km)
            if candidate is None:
                raise APIError(
                    422,
                    "NO_SUITABLE_CHARGER",
                    "No suitable charging stop was found for this route.",
                )

            charger_progress_km = candidate.distance_from_origin_km or 0
            charging_duration_minutes = estimate_charging_duration_minutes(
                candidate,
                provider_route.distance_meters / 1000,
                charger_progress_km,
                self._fixture_repository.fixtures.telemetry.estimated_range_km,
                self._safety_buffer_km,
                self._fixture_repository.fixtures.telemetry.consumption_rate_kwh,
            )
            charging_stop = candidate.stop.model_copy(update={"mandatory": True})
            charging_stop = charging_stop.model_copy(
                update={
                    "charging_duration_minutes": charging_duration_minutes
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
            if self._active_provider_route is None:
                raise APIError(
                    409,
                    "NO_ACTIVE_ROUTE",
                    "Plan a route before searching for places.",
                )
            location_context = (location or "destination").strip().lower()
            if location_context not in {"route", "stop", "destination"}:
                location_context = "destination"
            if location_context == "stop" and not self._active_stops:
                raise APIError(
                    409,
                    "NO_SELECTED_STOP",
                    "Select a charging stop before searching nearby amenities.",
                )
            search_kwargs = {
                "route": self._active_provider_route,
            }
            if "near_coords" in inspect.signature(self._places_provider.search).parameters:
                search_kwargs["near_coords"] = (
                    self._active_stops[-1].coords
                    if location_context == "stop"
                    else None
                )
            results = await self._places_provider.search(
                category, location_context, preference, **search_kwargs
            )
            if location_context == "stop":
                results = select_stop_amenities(results, self._active_stops[-1].coords)
            else:
                selection_location = location_context
                if location_context == "route" and category.casefold() != "attraction":
                    selection_location = "legacy-route"
                results = select_route_stops(
                    results,
                    tuple(self._active_provider_route.geometry),
                    preference,
                    selection_location,
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

    async def search_stop_amenities(
        self,
        stop_id: str,
        route_id: str,
        search_id: str | None = None,
        categories: tuple[str, ...] = (),
    ) -> list[StopPinpoint]:
        if self._active_provider_route is None or route_id != self._active_route_id:
            raise APIError(409, "STALE_ROUTE", "The selected route is no longer current.")
        if search_id is not None and search_id != self._active_search_id:
            raise APIError(409, "STALE_SEARCH", "The selected search is no longer current.")

        stop = next((item for item in self._active_stops if item.id == stop_id), None)
        if stop is None:
            stop = self._active_search_results.get(stop_id)
        if stop is None or stop.category != "charging":
            raise APIError(409, "STALE_STOP", "The selected charging stop is no longer current.")

        requested_categories = categories or ("food", "coffee", "rest", "service")
        results: list[StopPinpoint] = []
        try:
            for category in requested_categories:
                results.extend(
                    await self._places_provider.search(
                        category,
                        "stop",
                        None,
                        route=self._active_provider_route,
                        near_coords=stop.coords,
                    )
                )
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

        unique_results = {result.id: result for result in results}
        return select_stop_amenities(unique_results.values(), stop.coords)

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
            abs(coords[index] - stop.coords[index]) > POI_COORDINATE_TOLERANCE
            for index in (0, 1)
        ):
            raise APIError(422, "INVALID_POI_COORDINATES", "The selected place coordinates are invalid.")
        if not self._supports_waypoints():
            raise APIError(503, "ROUTING_UNAVAILABLE", "The routing service cannot route through a place.")

        selected_priority = priority or self._active_priority
        ordered_stops = sorted(
            (*self._active_stops, stop),
            key=lambda item: route_progress_km(
                item.coords, tuple(self._active_provider_route.geometry)
            ),
        )
        waypoints = tuple(
            GeocodedPlace(item.name, Coordinates(lng=item.coords[0], lat=item.coords[1]))
            for item in ordered_stops
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
            ordered_stops,
        )
        self._active_provider_route = provider_route
        self._active_priority = selected_priority
        self._active_stops = ordered_stops
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
