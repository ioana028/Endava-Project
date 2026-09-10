from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.assistant import router as assistant_router
from .core.errors import register_error_handlers
from .core.fixture_repository import FixtureRepository
from .core.settings import Settings
from .integrations.openai.assistant import OpenAIAssistantModule
from .integrations.openai.client import AsyncOpenAIClient
from .models.contracts import HealthResponse
from .services.assistant.ports import AssistantAIModule
from .services.assistant.service import AssistantService, LocalTextAIModule


def create_app(ai_module: AssistantAIModule | None = None) -> FastAPI:
    settings = Settings()
    fixture_repository = FixtureRepository(
        settings.telemetry_path, settings.partners_path
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
    application.state.assistant_service = AssistantService(configured_ai_module)
    application.include_router(assistant_router)
    register_error_handlers(application)

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok", service="backend", environment=settings.environment
        )

    return application


app = create_app()