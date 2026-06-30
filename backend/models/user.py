from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class ParentBase(BaseModel):
    """Base parent model"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = None


class ParentRegister(ParentBase):
    """Parent registration"""
    password: str = Field(..., min_length=8)
    password_confirm: str


class ParentLogin(BaseModel):
    """Parent login"""
    email: EmailStr
    password: str


class ParentConsent(BaseModel):
    """Parental consent for monitoring"""
    child_name: str = Field(..., description="Child's name")
    child_roblox_username: str = Field(..., description="Child's Roblox username")
    child_roblox_id: str = Field(..., description="Child's Roblox user ID")
    consent_granted: bool = Field(..., description="Parent agrees to monitor")
    data_retention_days: int = Field(default=30, ge=1, le=365)
    consent_timestamp: datetime = Field(default_factory=datetime.utcnow)
    notification_method: str = Field(default="email", description="email or sms")
    high_risk_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class ParentResponse(ParentBase):
    """Parent profile (no password)"""
    id: int
    email_verified: bool
    consent_signed: bool
    last_login: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    parent: ParentResponse
