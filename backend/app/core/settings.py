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
    max_audio_bytes: int = int(os.getenv("MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
    telemetry_path: Path = PROJECT_ROOT / "data" / "vehicles" / "telemetry.json"
    partners_path: Path = PROJECT_ROOT / "data" / "partners" / "partners.json"