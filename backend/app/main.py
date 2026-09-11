from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from math import atan2, cos, radians, sin, sqrt

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.assistant import router as assistant_router
from .core.errors import register_error_handlers
from .core.fixture_repository import FixtureRepository
from .core.settings import Settings
from .integrations.openai.assistant import OpenAIAssistantModule
from .integrations.openai.client import AsyncOpenAIClient
from .models.contracts import Coordinates, HealthResponse
from .services.assistant.ports import AssistantAIModule
from .services.assistant.service import AssistantService, LocalTextAIModule
from .services.trip.ports import (
    GeocodedPlace,
    InvalidDestinationError,
    ProviderRoute,
    RoutePriority,
    RoutingProviderError,
)
from .services.trip.service import RouteService


class GoogleRoutingProvider:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    async def geocode(self, place: str) -> GeocodedPlace:
        if self._api_key is None:
            return self._fallback_geocode(place)

        params = {
            "address": place,
            "key": self._api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return self._fallback_geocode(place)

        results = payload.get("results") or []
        if not results:
            raise InvalidDestinationError(place)

        location = results[0]["geometry"]["location"]
        return GeocodedPlace(
            display_name=results[0].get("formatted_address", place),
            coordinates=Coordinates(lng=location["lng"], lat=location["lat"]),
        )

    async def route(
        self,
        origin: GeocodedPlace,
        destination: GeocodedPlace,
        priority: RoutePriority,
    ) -> ProviderRoute:
        del priority
        if self._api_key is None:
            return self._fallback_route(origin, destination)

        params = {
            "origin": f"{origin.coordinates.lat},{origin.coordinates.lng}",
            "destination": f"{destination.coordinates.lat},{destination.coordinates.lng}",
            "mode": "driving",
            "key": self._api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/directions/json",
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return self._fallback_route(origin, destination)

        routes = payload.get("routes") or []
        if not routes:
            raise RoutingProviderError("Google Directions returned no routes")

        route = routes[0]
        legs = route.get("legs") or []
        if not legs:
            raise RoutingProviderError("Google Directions returned incomplete route data")

        leg = legs[0]
        return ProviderRoute(
            distance_meters=float(leg["distance"]["value"]),
            duration_seconds=float(leg["duration"]["value"]),
            geometry=(
                (origin.coordinates.lng, origin.coordinates.lat),
                (destination.coordinates.lng, destination.coordinates.lat),
            ),
        )

    @staticmethod
    def _fallback_geocode(place: str) -> GeocodedPlace:
        normalized = place.strip()
        seed = sum(ord(char) for char in normalized.casefold())
        lat = 48.2 + ((seed % 11) * 0.05)
        lng = 16.37 + ((seed % 13) * 0.08)
        return GeocodedPlace(
            display_name=normalized,
            coordinates=Coordinates(lng=lng, lat=lat),
        )

    @staticmethod
    def _fallback_route(
        origin: GeocodedPlace,
        destination: GeocodedPlace,
    ) -> ProviderRoute:
        distance_meters = GoogleRoutingProvider._distance_between(
            origin.coordinates,
            destination.coordinates,
        )
        duration_seconds = max(distance_meters / 1000 * 60, 1)
        return ProviderRoute(
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            geometry=(
                (origin.coordinates.lng, origin.coordinates.lat),
                (destination.coordinates.lng, destination.coordinates.lat),
            ),
        )

    @staticmethod
    def _distance_between(origin: Coordinates, destination: Coordinates) -> float:
        radius_km = 6371.0
        lat1, lon1 = radians(origin.lat), radians(origin.lng)
        lat2, lon2 = radians(destination.lat), radians(destination.lng)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return radius_km * c * 1000


def create_app(
    ai_module: AssistantAIModule | None = None,
    route_service: RouteService | None = None,
) -> FastAPI:
    settings = Settings()
    fixture_repository = FixtureRepository(
        settings.telemetry_path, settings.partners_path
    )
    route_service = route_service or RouteService(
        GoogleRoutingProvider(settings.google_server_api_key),
        fixture_repository,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.fixtures = fixture_repository.load()
        yield

    application = FastAPI(title="Suzanne Backend", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.state.settings = settings
    configured_ai_module = ai_module or LocalTextAIModule()
    if ai_module is None and settings.openai_api_key:
        try:
            configured_ai_module = OpenAIAssistantModule(
                AsyncOpenAIClient(settings.openai_api_key)
            )
        except ModuleNotFoundError as error:
            if error.name != "openai":
                raise
    application.state.assistant_service = AssistantService(
        configured_ai_module,
        route_service=route_service,
    )
    application.include_router(assistant_router)
    register_error_handlers(application)

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok", service="backend", environment=settings.environment
        )

    return application


app = create_app()