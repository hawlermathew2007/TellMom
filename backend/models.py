from pydantic import BaseModel


class IngestRequest(BaseModel):
    platform: str
    chat_group: dict[str, list[str]]


class ClassifierResult(BaseModel):
    user_id: str
    is_pedo: bool


class FlaggedUser(BaseModel):
    user_id: str
    flagged_chats: list[str]
    resolved: bool


class IngestResponse(BaseModel):
    status: str
    classified_count: int
    newly_flagged: list[str]
