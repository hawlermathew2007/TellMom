from datetime import datetime

from pydantic import BaseModel

from adapters.base import ChatPlatform
from schemas.grooming import GroomingAnalysis


class AlertResponse(BaseModel):
    id: int
    child_account_id: int
    platform: ChatPlatform
    server_id: str
    message_preview: str
    explanation: GroomingAnalysis | None = None
    acknowledged: bool
    created_at: datetime

    model_config = {"from_attributes": True}
