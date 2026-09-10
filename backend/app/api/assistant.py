from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.app.models.assistant import AssistantResponse
from backend.app.services.assistant import AssistantProviderError, AssistantService


class InteractRequest(BaseModel):
    text: str = Field(min_length=1)
    session_id: str | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}


# Application startup should provide the configured service through this dependency.
def get_assistant_service() -> AssistantService:
    raise RuntimeError("assistant service dependency is not configured")


router = APIRouter(prefix="/api/assistant", tags=["assistant"])
ServiceDependency = Annotated[AssistantService, Depends(get_assistant_service)]


@router.post("/interact", response_model=AssistantResponse)
async def interact(request: InteractRequest, service: ServiceDependency) -> AssistantResponse:
    try:
        return await service.interact_text(request.text)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except AssistantProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="assistant provider unavailable",
        ) from error


@router.post("/voice", response_model=AssistantResponse)
async def voice(
    audio: Annotated[UploadFile, File(...)],
    service: ServiceDependency,
) -> AssistantResponse:
    try:
        return await service.interact_voice(
            audio.file,
            audio.filename or "recording.webm",
        )
    except AssistantProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="assistant provider unavailable",
        ) from error
