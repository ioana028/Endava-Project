from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.assistant import router as assistant_router
from .core.errors import register_error_handlers
from .core.fixture_repository import FixtureRepository
from .core.settings import Settings
from .integrations.google_maps.routing import GoogleMapsRoutingProvider
from .integrations.places.google import GooglePlacesProvider
from .integrations.places.provider import OfflinePlacesProvider
from .integrations.openai.realtime import (
    OpenAIRealtimeProvider,
    RealtimeSessionProvider,
)
from .models.contracts import (
    HealthResponse,
    ProviderHealthResponse,
    VehicleTelemetryResponse,
)
from .models.fixtures import Fixtures, VehicleState
from .services.trip.service import RouteService
from .services.commerce.service import CommerceService
from .services.wallet.service import WalletService


def create_app(
    route_service: RouteService | None = None,
    realtime_provider: RealtimeSessionProvider | None = None,
) -> FastAPI:
    settings = Settings()
    fixture_repository = FixtureRepository(
        settings.telemetry_path, settings.partners_path
    )
    places_provider = (
        GooglePlacesProvider(
            settings.google_server_api_key,
            timeout_seconds=settings.google_places_timeout_seconds,
            search_radius_meters=settings.google_places_route_search_radius_meters,
            nearby_search_radius_meters=settings.google_places_nearby_search_radius_meters,
            sample_interval_km=settings.google_places_sample_interval_km,
            max_search_points=settings.google_places_max_search_points,
        )
        if settings.places_provider == "google"
        or (settings.google_server_api_key and settings.places_provider == "auto")
        else OfflinePlacesProvider(fixture_repository, settings.places_path)
    )
    route_service = route_service or RouteService(
        GoogleMapsRoutingProvider(settings.google_server_api_key),
        fixture_repository,
        places_provider=places_provider,
        charging_provider=(
            places_provider
            if isinstance(places_provider, GooglePlacesProvider)
            else None
        ),
    )
    wallet_service = WalletService()
    commerce_service = CommerceService(route_service, wallet_service)

    def safe_load_fixtures() -> Fixtures:
        try:
            return fixture_repository.load()
        except (RuntimeError, OSError, ValueError, TypeError):
            return Fixtures(
                telemetry=VehicleState(
                    vehicle_id="offline-demo",
                    propulsion="BEV",
                    battery_percent=42.0,
                    estimated_range_km=95.0,
                    max_charged_range_km=0.0,
                    consumption_rate_kwh=0.16,
                    tyres="SUMMER",
                    odometer_km=0.0,
                ),
                partners=(),
            )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.fixtures = safe_load_fixtures()
        yield

    application = FastAPI(title="Suzanne Backend", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.state.settings = settings
    application.state.route_service = route_service
    application.state.wallet_service = wallet_service
    application.state.commerce_service = commerce_service
    application.state.realtime_provider = realtime_provider or OpenAIRealtimeProvider(
        settings.openai_api_key,
        settings.realtime_model,
        settings.realtime_secret_seconds,
    )
    application.include_router(assistant_router)
    register_error_handlers(application)

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok", service="backend", environment=settings.environment
        )

    @application.get("/health/config", response_model=ProviderHealthResponse)
    async def provider_health() -> ProviderHealthResponse:
        provider_mode = settings.places_provider
        resolved_places_provider = (
            "google"
            if provider_mode == "google"
            or (provider_mode == "auto" and settings.google_server_api_key)
            else "offline"
        )
        partner_records = tuple(getattr(application.state, "fixtures", safe_load_fixtures()).partners)
        scenic_capability = bool(settings.google_server_api_key) or (
            resolved_places_provider == "offline"
        )
        return ProviderHealthResponse(
            status="ok",
            environment=settings.environment,
            openai_configured=bool(settings.openai_api_key),
            google_routes_configured=bool(settings.google_server_api_key),
            google_places_configured=(
                resolved_places_provider == "google"
                and bool(settings.google_server_api_key)
            ),
            places_provider=resolved_places_provider,
            scenic_capability=scenic_capability,
            partner_enrichment_ready=bool(partner_records),
        )

    @application.get("/api/vehicle/telemetry", response_model=VehicleTelemetryResponse)
    async def vehicle_telemetry() -> VehicleTelemetryResponse:
        telemetry = safe_load_fixtures().telemetry
        return VehicleTelemetryResponse.model_validate(telemetry.model_dump())

    return application


app = create_app()