import base64
import re

from ...core.errors import APIError
from ...models.contracts import (
	AssistantIntent,
	AssistantResponse,
	RoutePriority,
	RouteResponse,
)
from ...services.trip.service import RouteService
from .ports import AIResult, AssistantAIModule, RouteNarration


DAY_ONE_SPOKEN_RESPONSE = "Calculating route based on your preferences, hold on"


class LocalTextAIModule:
	_destination_pattern = re.compile(
		r"\bto\s+(.+?)(?=\s+(?:fast|fastest|quick|quickest|cheap|cheapest|"
		r"scenic|balanced)\b|[,.!?]|$)",
		re.IGNORECASE,
	)

	async def process_text(self, text: str, session_id: str | None) -> AIResult:
		del session_id
		destination_match = self._destination_pattern.search(text)
		if destination_match is None:
			raise APIError(400, "INVALID_REQUEST", "A destination is required.")

		lowered = text.casefold()
		priority = RoutePriority.BALANCED
		if re.search(r"\b(?:fast|fastest|quick|quickest)\b", lowered):
			priority = RoutePriority.FASTEST
		elif re.search(r"\b(?:cheap|cheapest|affordable)\b", lowered):
			priority = RoutePriority.CHEAPEST
		elif re.search(r"\bscenic\b", lowered):
			priority = RoutePriority.SCENIC

		intent = AssistantIntent(
			destination=destination_match.group(1).strip().title(),
			priority=priority,
		)
		return AIResult(transcript=text, intent=intent)

	async def process_voice(
		self,
		audio: bytes,
		filename: str,
		content_type: str,
		session_id: str | None,
	) -> AIResult:
		del audio, filename, content_type, session_id
		raise APIError(503, "AI_UNAVAILABLE", "The voice assistant is unavailable.")

	async def synthesize_route(self, route: RouteResponse) -> RouteNarration:
		distance = f"{route.stats.total_distance_km:g}"
		duration_minutes = int(route.stats.total_duration_minutes + 0.5)
		hours, minutes = divmod(duration_minutes, 60)
		if hours and minutes:
			duration = f"{hours} hours {minutes} minutes"
		elif hours:
			duration = f"{hours} hour" if hours == 1 else f"{hours} hours"
		else:
			duration = f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"

		text = (
			f"I've planned your route to {route.destination}. "
			f"It's {distance} kilometres and it will take approximately {duration}."
		)
		for alert in route.alerts:
			text = f"{text} {alert.message}"

		return RouteNarration(text=text)


class AssistantService:
	def __init__(
		self,
		ai_module: AssistantAIModule,
		route_service: RouteService | None = None,
	) -> None:
		self._ai_module = ai_module
		self._route_service = route_service

	async def interact(self, text: str, session_id: str | None) -> AssistantResponse:
		if not text.strip():
			raise APIError(400, "INVALID_REQUEST", "Text must not be empty.")
		return await self._response(await self._ai_module.process_text(text, session_id))

	async def process_voice(
		self,
		audio: bytes,
		filename: str,
		content_type: str,
		session_id: str | None,
	) -> AssistantResponse:
		result = await self._ai_module.process_voice(
			audio, filename, content_type, session_id
		)
		return await self._response(result)

	async def _response(self, result: AIResult) -> AssistantResponse:
		route = (
			await self._route_service.plan(result.intent)
			if self._route_service
			else None
		)
		narration = (
			await self._ai_module.synthesize_route(route)
			if route
			else RouteNarration(DAY_ONE_SPOKEN_RESPONSE, result.audio)
		)
		audio_base64 = (
			base64.b64encode(narration.audio).decode("ascii")
			if narration.audio
			else None
		)
		return AssistantResponse(
			transcript=result.transcript,
			intent=result.intent,
			spoken_response=narration.text,
			audio_base64=audio_base64,
			route=route,
			toast_message=(
				f"INTENT: {result.intent.destination.upper()} "
				f"({result.intent.priority.value})"
			),
		)
