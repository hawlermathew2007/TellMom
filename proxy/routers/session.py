from fastapi import APIRouter, HTTPException

from proxy.schemas.response import ResponseStatus
from proxy.schemas.session import (
    SessionAuthRequest,
    SessionAuthResponse,
    SessionDhRequest,
    SessionDhResponse,
    SessionMessageRequest,
    SessionMessageResponse,
    SessionRequestTypes
)
from proxy.services.session import (
    associate_session,
    get_server_for_session,
    send_proxy_request,
)
from shared.schemas.messages import AuthRequest, DhRequest, MessageRequest

router = APIRouter(prefix="/session", tags=["session"])


# TODO: must change all these statuses to enums
@router.post("/associate", response_model=SessionAuthResponse)
async def authenticate_session(body: SessionAuthRequest) -> SessionAuthResponse:
    try:
        msg = AuthRequest(
            type=SessionRequestTypes.ASSOCIATE.value,  # type: ignore[arg-type]
            server_id=body.server_id,
            password_code=body.password_code,
            client_id=body.client_id,
        )
        response = await send_proxy_request(body.server_id, msg)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if response.get("status") != ResponseStatus.SUCCESS.value:
        return SessionAuthResponse(
            session_id=None,
            status=ResponseStatus.FAILED,
            reason=response.get("reason", "Authentication failed"),
        )

    session_id = response.get("session_id")
    if session_id is None:
        raise HTTPException(status_code=500, detail="Missing session_id from proxy response")

    associate_session(session_id, body.server_id)
    return SessionAuthResponse(session_id=session_id, status=ResponseStatus.SUCCESS)


@router.post("/key-exchange", response_model=SessionDhResponse)
async def exchange_dh(body: SessionDhRequest) -> SessionDhResponse:
    server_id = get_server_for_session(body.session_id)
    if server_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        msg = DhRequest(
            type=SessionRequestTypes.KEY_EXCHANGE.value,  # type: ignore[arg-type]
            session_id=body.session_id,
            client_dh_pubkey=body.client_dh_pubkey,
        )
        response = await send_proxy_request(server_id, msg)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if response.get("status") != ResponseStatus.SUCCESS.value:
        raise HTTPException(status_code=400, detail=response.get("reason", "DH exchange failed"))

    server_dh_pubkey = response.get("server_dh_pubkey")
    if server_dh_pubkey is None:
        raise HTTPException(status_code=500, detail="Missing server public key")

    return SessionDhResponse(session_id=body.session_id, server_dh_pubkey=server_dh_pubkey)


@router.post("/message", response_model=SessionMessageResponse)
async def forward_message(body: SessionMessageRequest) -> SessionMessageResponse:
    server_id = get_server_for_session(body.session_id)
    if server_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # TODO: move all of tis to respective requests pydantic model and add a wrapper message around this 
        msg = MessageRequest(
            type=SessionRequestTypes.MESSAGE.value,  # type: ignore[arg-type]
            session_id=body.session_id,
            sequence=body.sequence,
            nonce=body.nonce,
            ciphertext=body.ciphertext,
            auth_tag=body.auth_tag,
        )
        response = await send_proxy_request(server_id, msg)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if response.get("status") != ResponseStatus.SUCCESS.value:
        raise HTTPException(status_code=400, detail=response.get("reason", "Encrypted message rejected"))

    return SessionMessageResponse(
        session_id=body.session_id,
        sequence=response["sequence"],
        nonce=response["nonce"],
        ciphertext=response["ciphertext"],
        auth_tag=response["auth_tag"],
    )
