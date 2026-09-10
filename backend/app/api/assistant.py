from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from ..core.errors import APIError
from ..models.contracts import AssistantResponse, InteractRequest
from ..services.assistant.service import AssistantService


router = APIRouter(prefix="/api/assistant", tags=["assistant"])
SUPPORTED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "video/webm",
}


def get_assistant_service(request: Request) -> AssistantService:
    return request.app.state.assistant_service


@router.post(
    "/interact",
    response_model=AssistantResponse,
    response_model_exclude_none=True,
)
async def interact(payload: InteractRequest, request: Request) -> AssistantResponse:
    return await get_assistant_service(request).interact(
        payload.text, payload.session_id
    )


@router.post(
    "/voice",
    response_model=AssistantResponse,
    response_model_exclude_none=True,
)
async def voice(
    request: Request,
    audio: Annotated[UploadFile, File()],
    session_id: Annotated[str | None, Form(alias="sessionId")] = None,
) -> AssistantResponse:
    content_type = (audio.content_type or "").lower()
    if content_type not in SUPPORTED_AUDIO_TYPES:
        raise APIError(400, "INVALID_AUDIO", "The uploaded audio format is not supported.")

    max_bytes = request.app.state.settings.max_audio_bytes
    audio_bytes = await audio.read(max_bytes + 1)
    if not audio_bytes:
        raise APIError(400, "INVALID_AUDIO", "The uploaded audio is empty.")
    if len(audio_bytes) > max_bytes:
        raise APIError(413, "PAYLOAD_TOO_LARGE", "The uploaded audio is too large.")

    return await get_assistant_service(request).process_voice(
        audio_bytes,
        audio.filename or "recording",
        content_type,
        session_id,
    )