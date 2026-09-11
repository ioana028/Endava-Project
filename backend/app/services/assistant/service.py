import base64
import re

from ...core.errors import APIError
from ...models.contracts import AssistantIntent, AssistantResponse, RoutePriority
from ...services.trip.service import RouteService
from .ports import AIResult, AssistantAIModule


SPOKEN_RESPONSE = "Calculating route based on your preferences, hold on"


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
		audio_base64 = (
			base64.b64encode(result.audio).decode("ascii") if result.audio else None
		)
		return AssistantResponse(
			transcript=result.transcript,
			intent=result.intent,
			spoken_response=SPOKEN_RESPONSE,
			audio_base64=audio_base64,
			route=route,
			toast_message=(
				f"INTENT: {result.intent.destination.upper()} "
				f"({result.intent.priority.value})"
			),
		)

from ...core.errors import APIError
from ...models.contracts import AssistantIntent, AssistantResponse, RoutePriority
from ...services.trip.service import RouteService
from .ports import AIResult, AssistantAIModule


SPOKEN_RESPONSE = "Calculating route based on your preferences, hold on"


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
		route = await self._route_service.plan(result.intent) if self._route_service else None
		audio_base64 = (
			base64.b64encode(result.audio).decode("ascii") if result.audio else None
		)
		return AssistantResponse(
			transcript=result.transcript,
			intent=result.intent,
			spoken_response=SPOKEN_RESPONSE,
			audio_base64=audio_base64,
			route=route,
			toast_message=(
				f"INTENT: {result.intent.destination.upper()} "
				f"({result.intent.priority.value})"
			),
		)
