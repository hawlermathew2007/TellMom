from datetime import datetime

from pydantic import BaseModel

from adapters.base import ChatPlatform


class AlertResponse(BaseModel):
    id: int
    child_account_id: int
    flagged_user_id: str
    platform: ChatPlatform
    server_id: str
    message_preview: str
    acknowledged: bool
    created_at: datetime

    model_config = {"from_attributes": True}
