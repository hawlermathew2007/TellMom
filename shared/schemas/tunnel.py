from pydantic import BaseModel
from shared.schemas.session import SessionRequestTypes

class TunnelRequest(BaseModel):
    type: SessionRequestTypes = SessionRequestTypes.FORWARD
    request_id: str
    session_id: str
    method: str
    path: str
    query: str
    headers: dict[str, str]
    body: str

class TunnelResponse(BaseModel):
    type: SessionRequestTypes = SessionRequestTypes.FORWARD
    request_id: str
    status: int
    headers: dict[str, str]
    body: str
