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