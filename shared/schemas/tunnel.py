from pydantic import BaseModel
from enum import Enum


class TunnelRequestTypes(str, Enum):
    ASSOCIATE = "ASSOCIATE"
    KEY_EXCHANGE = "KEY_EXCHANGE"
    FORWARD = "FORWARD"


class TunnelRequest(BaseModel):
    type: TunnelRequestTypes = TunnelRequestTypes.FORWARD
    request_id: str
    session_id: str
    method: str
    path: str
    query: str
    headers: dict[str, str]
    body: str


class TunnelResponse(BaseModel):
    type: TunnelRequestTypes = TunnelRequestTypes.FORWARD
    request_id: str
    status: int = 200
    headers: dict[str, str] = {}
    body: str = ""


class EncryptedMessage(BaseModel):
    sequence: int
    nonce: str
    ciphertext: str
    auth_tag: str
