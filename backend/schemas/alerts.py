from datetime import datetime
from pydantic import BaseModel
from core.registry import ChatPlatform


class ChatMessageResponse(BaseModel):
    id: int
    sender_platform_user_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: int
    child_account_id: int
    platform: ChatPlatform
    server_id: str
    message_preview: str
    probability: float
    acknowledged: bool
    detected_stages: list = []
    created_at: datetime
    messages: list[ChatMessageResponse] = []

    model_config = {"from_attributes": True}
