from typing import Literal
from pydantic import BaseModel, Field
from adapters.base import ChatPlatform


class IngestRequest(BaseModel):
    platform: ChatPlatform
    user_id: str
    server_id: str
    message: str = Field(min_length=1)


# TODO: re-consider this one
# class IngestResponse(BaseModel):
#     status: Literal["below_threshold", "classified"]
#     message_count: int = 0
#     classified_count: int = 0
#     newly_flagged: list[str] = Field(default_factory=list)
#     parents_notified: int = 0


class ClassifierCheckInRequest(BaseModel):
    client: str
    version: str
    timestamp: str


class ClassifierCheckInResponse(BaseModel):
    status: Literal["ok"] = "ok"
    message: str = "Classifier registered"
    token: str


class ClassifierResultItem(BaseModel):
    user_id: str
    is_pedo: bool


class ClassifyRequest(BaseModel):
    """Batch classification job pushed to a connected learner over WebSocket."""

    request_id: str
    platform: str
    server_id: str
    chat_group: dict[str, list[str]]


class ClassifyResponse(BaseModel):
    """Batch classification result returned by the learner."""

    request_id: str
    results: list[ClassifierResultItem]
