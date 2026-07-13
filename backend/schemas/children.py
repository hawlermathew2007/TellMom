from datetime import datetime
from pydantic import BaseModel, Field
from adapters.platforms import ChatPlatform


class ChildAccountCreate(BaseModel):
    platform: ChatPlatform
    platform_user_id: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class ChildAccountUpdate(BaseModel):
    platform_user_id: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)


class ChildAccountResponse(BaseModel):
    id: int
    platform: ChatPlatform
    platform_user_id: str
    display_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
