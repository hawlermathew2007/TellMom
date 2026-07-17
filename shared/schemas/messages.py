from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from shared.schemas.response import ResponseStatus


class AuthRequest(BaseModel):
    type: Literal["ASSOCIATE"]
    request_id: str | None = None
    server_id: str
    password_code: str
    client_id: str | None = None


class DhRequest(BaseModel):
    type: Literal["KEY_EXCHANGE"]
    request_id: str | None = None
    session_id: str
    client_dh_pubkey: str


class MessageRequest(BaseModel):
    type: Literal["MESSAGE"]
    request_id: str | None = None
    session_id: str
    sequence: int
    nonce: str
    ciphertext: str
    auth_tag: str


ProxyRequest = Annotated[
    Union[AuthRequest, DhRequest, MessageRequest],
    Field(discriminator="type"),
]


class AuthResponse(BaseModel):
    type: Literal["auth_response"] = "auth_response"
    request_id: str
    session_id: str | None = None
    status: ResponseStatus
    reason: str | None = None


class DhResponse(BaseModel):
    type: Literal["dh_response"] = "dh_response"
    request_id: str
    session_id: str
    status: ResponseStatus
    server_dh_pubkey: str | None = None
    reason: str | None = None


class MessageResponse(BaseModel):
    type: Literal["message_response"] = "message_response"
    request_id: str
    session_id: str
    status: ResponseStatus
    sequence: int | None = None
    nonce: str | None = None
    ciphertext: str | None = None
    auth_tag: str | None = None
    reason: str | None = None


ProxyResponse = Annotated[
    Union[AuthResponse, DhResponse, MessageResponse],
    Field(discriminator="type"),
]
