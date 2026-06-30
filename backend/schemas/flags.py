from pydantic import BaseModel


class FlaggedUser(BaseModel):
    user_id: str
    server_id: str
    platform: str
    flagged_chats: list[str]
    resolved: bool
