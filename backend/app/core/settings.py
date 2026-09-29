import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    port: int = int(os.getenv("PORT", "8000"))
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    realtime_model: str = os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2.1-mini")
    realtime_secret_seconds: int = int(
        os.getenv("OPENAI_REALTIME_SECRET_SECONDS", "300")
    )
    google_server_api_key: str | None = os.getenv("GOOGLE_SERVER_API_KEY")
    google_places_timeout_seconds: float = float(
        os.getenv("GOOGLE_PLACES_TIMEOUT_SECONDS", "10")
    )
    google_places_route_search_radius_km: float = float(
        os.getenv(
            "GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_KM",
            os.getenv("GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_METERS", "7500"),
        )
    ) / 1000.0
    google_places_route_search_radius_meters: float = float(
        os.getenv(
            "GOOGLE_PLACES_ROUTE_SEARCH_RADIUS_METERS",
            os.getenv("GOOGLE_PLACES_SEARCH_RADIUS_METERS", "7500"),
        )
    )
    google_places_nearby_search_radius_meters: float = float(
        os.getenv(
            "GOOGLE_PLACES_NEARBY_SEARCH_RADIUS_METERS",
            os.getenv("GOOGLE_PLACES_STOP_SEARCH_RADIUS_METERS", "500"),
        )
    )
    google_places_search_radius_meters: float = float(
        os.getenv("GOOGLE_PLACES_SEARCH_RADIUS_METERS", "7500")
    )
    google_places_sample_interval_km: float = float(
        os.getenv("GOOGLE_PLACES_SAMPLE_INTERVAL_KM", "25")
    )
    google_places_max_search_points: int = int(
        os.getenv("GOOGLE_PLACES_MAX_SEARCH_POINTS", "4")
    )
    provider_request_budget: int = int(
        os.getenv("PROVIDER_REQUEST_BUDGET", "20")
    )
    places_provider: str = os.getenv("PLACES_PROVIDER", "auto").strip().lower()
    weather_provider: str = os.getenv("WEATHER_PROVIDER", "offline").strip().lower()
    weather_enabled: bool = os.getenv("WEATHER_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
    weather_api_key: str | None = os.getenv("WEATHER_API_KEY")
    weather_timeout_seconds: float = float(os.getenv("WEATHER_TIMEOUT_SECONDS", "10"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )
    telemetry_path: Path = PROJECT_ROOT / "data" / "vehicles" / "telemetry.json"
    partners_path: Path = PROJECT_ROOT / "data" / "partners" / "partners.json"
    places_path: Path = PROJECT_ROOT / "data" / "places" / "places.json"