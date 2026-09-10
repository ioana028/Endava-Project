from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class RoutePriority(StrEnum):
    FASTEST = "FASTEST"
    CHEAPEST = "CHEAPEST"
    SCENIC = "SCENIC"
    BALANCED = "BALANCED"


class AssistantIntent(ContractModel):
    destination: str = Field(min_length=1)
    priority: RoutePriority


class AssistantResponse(ContractModel):
    transcript: str
    intent: AssistantIntent
    spoken_response: str
    audio_base64: str | None = None
    route: None = None
    toast_message: str | None = None


class InteractRequest(ContractModel):
    text: str = Field(min_length=1)
    session_id: str | None = None


class HealthResponse(ContractModel):
    status: str
    service: str
    environment: str