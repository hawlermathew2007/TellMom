from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MessageBase(BaseModel):
    """Base message model"""
    roblox_user_id: str = Field(..., description="Roblox user ID")
    username: str = Field(..., description="Roblox username")
    text: str = Field(..., description="Chat message text", min_length=1, max_length=500)
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


class MessageCapture(MessageBase):
    """Message capture from Roblox client"""
    child_id: str = Field(..., description="Child's account ID")
    api_key: str = Field(..., description="Roblox API key for verification")


class MessageAnalysis(BaseModel):
    """AI analysis result for a message"""
    message_id: int
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Grooming risk (0.0-1.0)")
    risk_level: str = Field(..., description="GREEN, YELLOW, or RED")
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str = Field(..., description="Why flagged (if risk > threshold)")
    flagged_phrases: list[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class MessageResponse(MessageBase):
    """Message with analysis results"""
    id: int
    analysis: Optional[MessageAnalysis] = None
    parent_notified: bool = False
    parent_acknowledged: bool = False


class MessageHistoryResponse(BaseModel):
    """Message history for a child"""
    total_count: int
    high_risk_count: int
    messages: list[MessageResponse]
