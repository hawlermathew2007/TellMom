from pydantic import BaseModel
from shared.schemas.response import ResponseStatus


class SessionAuthRequest(BaseModel):
    server_id: str
    password_code: str
    client_id: str | None = None


class SessionAuthResponse(BaseModel):
    session_id: str | None = None
    status: ResponseStatus
    reason: str | None = None


class SessionDhRequest(BaseModel):
    session_id: str
    client_dh_pubkey: str


class SessionDhResponse(BaseModel):
    session_id: str
    server_dh_pubkey: str


class SessionMessageRequest(BaseModel):
    session_id: str
    sequence: int
    nonce: str
    ciphertext: str
    auth_tag: str


class SessionMessageResponse(BaseModel):
    session_id: str
    sequence: int
    nonce: str
    ciphertext: str
    auth_tag: str
