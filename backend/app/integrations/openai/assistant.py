import io

from ...models.contracts import AssistantIntent, RouteResponse
from ...services.assistant.ports import AIResult
from .client import OpenAIClient


SUPPORTED_LANGUAGE = "en"


def _format_duration(total_minutes: float) -> str:
    rounded_minutes = int(total_minutes + 0.5)
    hours, minutes = divmod(rounded_minutes, 60)
    if hours and minutes:
        return f"{hours} hours {minutes} minutes"
    if hours:
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"


def build_route_narration(route: RouteResponse) -> str:
    distance = f"{route.stats.total_distance_km:g}"
    duration = _format_duration(route.stats.total_duration_minutes)
    narration = (
        f"I've planned your route to {route.destination}. "
        f"It's {distance} kilometres and it will take approximately {duration}."
    )
    vehicle_alert = next(
        (alert for alert in route.alerts if alert.type == "VEHICLE"), None
    )
    if vehicle_alert:
        narration = f"{narration} {vehicle_alert.message}"
    return narration


class OpenAIAssistantModule:
    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    async def process_text(self, text: str, session_id: str | None) -> AIResult:
        del session_id
        intent = AssistantIntent.model_validate(await self._client.extract_intent(text))
        return AIResult(transcript=text, intent=intent)

    async def synthesize_route(self, route: RouteResponse) -> tuple[str, bytes]:
        narration = build_route_narration(route)
        return narration, await self._client.synthesize(narration)

    async def process_voice(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        session_id: str | None,
    ) -> AIResult:
        del content_type
        transcript = await self._client.transcribe(
            io.BytesIO(audio), filename, language=SUPPORTED_LANGUAGE
        )
        result = await self.process_text(transcript, session_id)
        return AIResult(transcript=transcript, intent=result.intent, audio=result.audio)