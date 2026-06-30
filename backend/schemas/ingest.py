from pydantic import BaseModel


class IngestRequest(BaseModel):
    platform: str
    server_id: str
    chat_group: dict[str, list[str]]


class IngestResponse(BaseModel):
    status: str
    classified_count: int
    newly_flagged: list[str]
    parents_notified: int = 0
