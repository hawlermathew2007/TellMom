from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    platform: str
    user_id: str
    server_id: str
    message: str = Field(min_length=1)


class IngestResponse(BaseModel):
    status: str
    message_count: int = 0
    classified_count: int = 0
    newly_flagged: list[str] = Field(default_factory=list)
    parents_notified: int = 0
