from pydantic import BaseModel
# from schemas.grooming import GroomingAnalysis


class FlaggedConversation(BaseModel):
    platform: str
    server_id: str
    flagged_chats: list[str]
    resolved: bool
    # explanation: GroomingAnalysis | None = None
