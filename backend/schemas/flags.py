from pydantic import BaseModel

from schemas.grooming import GroomingAnalysis


class FlaggedUser(BaseModel):
    user_id: str
    server_id: str
    platform: str
    flagged_chats: list[str]
    resolved: bool
    explanation: GroomingAnalysis | None = None
