from pydantic import BaseModel, Field
from adapters.platforms import ChatPlatform
from shared.schemas.response import ResponseStatus


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
    status: ResponseStatus
    message: str = "Classifier registered"
    token: str


class ClassifierResultItem(BaseModel):
    has_pedo: bool
    probability: float


class ClassifyResponse(BaseModel):
    request_id: str
    result: ClassifierResultItem
