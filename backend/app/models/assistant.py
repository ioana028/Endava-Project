from typing import Literal

from pydantic import BaseModel, Field


RoutePriority = Literal["FASTEST", "CHEAPEST", "SCENIC", "BALANCED"]


class AssistantIntent(BaseModel):
    destination: str = Field(min_length=1)
    priority: RoutePriority


class AssistantResponse(BaseModel):
    transcript: str
    intent: AssistantIntent
    spoken_response: str = Field(alias="spokenResponse")
    audio_base64: str | None = Field(default=None, alias="audioBase64")
    route: None = None
    toast_message: str | None = Field(default=None, alias="toastMessage")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    @classmethod
    def with_camel_case(cls, **data: object) -> "AssistantResponse":
        return cls.model_validate(data)
