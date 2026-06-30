from pydantic import BaseModel, EmailStr, Field


class ParentRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class ParentLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ParentResponse(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}
