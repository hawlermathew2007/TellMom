from typing import Literal
from pydantic import BaseModel, Field
from adapters.base import ChatPlatform


class IngestRequest(BaseModel):
    platform: ChatPlatform
    user_id: str
    server_id: str
    message: str = Field(min_length=1)


class ClassifierCheckInRequest(BaseModel):
    client: str
    version: str
    timestamp: str


class ClassifierCheckInResponse(BaseModel):
    status: Literal["ok"] = "ok"
    message: str = "Classifier registered"


class ClassifierResultItem(BaseModel):
    has_pedo: bool
    probability: float


class ClassifyResponse(BaseModel):
    request_id: str
    result: ClassifierResultItem
