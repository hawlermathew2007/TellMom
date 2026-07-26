import base64
import uuid
from fastapi import APIRouter, HTTPException, Request, WebSocket

from fastapi.responses import Response

from shared.schemas.response import ResponseStatus
from shared.schemas.tunnel import TunnelRequestTypes
from proxy.schemas.session import (
    SessionAuthRequest,
    SessionAuthResponse,
    SessionDhRequest,
    SessionDhResponse,
)
from proxy.services.session import (
    associate_session,
    get_server_for_session,
    send_proxy_request,
    send_proxy_ws_message,
    register_ws_connection,
    unregister_ws_connection,
)
from shared.schemas.tunnel import TunnelRequest
from shared.schemas.messages import AuthRequest, DhRequest


router = APIRouter(prefix="/session", tags=["session"])


@router.post("/associate", response_model=SessionAuthResponse)
async def authenticate_session(body: SessionAuthRequest) -> SessionAuthResponse:
    try:
        msg = AuthRequest(
            type=TunnelRequestTypes.ASSOCIATE.value,
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
        raise HTTPException(
            status_code=500, detail="Missing session_id from proxy response"
        )

    associate_session(session_id, body.server_id)
    return SessionAuthResponse(session_id=session_id, status=ResponseStatus.SUCCESS)


@router.post("/key-exchange", response_model=SessionDhResponse)
async def exchange_dh(body: SessionDhRequest) -> SessionDhResponse:
    server_id = get_server_for_session(body.session_id)
    if server_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        msg = DhRequest(
            type=TunnelRequestTypes.KEY_EXCHANGE.value,  # type: ignore[arg-type]
            session_id=body.session_id,
            client_dh_pubkey=body.client_dh_pubkey,
        )
        response = await send_proxy_request(server_id, msg)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if response.get("status") != ResponseStatus.SUCCESS.value:
        raise HTTPException(
            status_code=400, detail=response.get("reason", "DH exchange failed")
        )

    server_dh_pubkey = response.get("server_dh_pubkey")
    if server_dh_pubkey is None:
        raise HTTPException(status_code=500, detail="Missing server public key")

    return SessionDhResponse(
        session_id=body.session_id, server_dh_pubkey=server_dh_pubkey
    )


@router.api_route(
    "/{session_id}/forward/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def forward_request(session_id: str, path: str, request: Request):
    server_id = get_server_for_session(session_id)
    if server_id is None:
        raise HTTPException(status_code=404, detail="Session not found")

    body_bytes = await request.body()
    body_b64 = base64.urlsafe_b64encode(body_bytes).decode("ascii")

    headers = {k: v for k, v in request.headers.items()}

    # Send the raw HTTP request data over the tunnel
    tunnel_req = TunnelRequest(
        request_id="",  # filled by send_proxy_request
        session_id=session_id,
        method=request.method,
        path=f"/{path}",
        query=request.url.query,
        headers=headers,
        body=body_b64,
    )

    try:
        response = await send_proxy_request(server_id, tunnel_req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    status = response.get("status", 500)
    resp_headers = response.get("headers", {})
    resp_headers["content-type"] = "application/json"
    resp_body_b64 = response.get("body", "").strip()
    padding = "=" * (-len(resp_body_b64) % 4)
    resp_body = (
        base64.urlsafe_b64decode(resp_body_b64 + padding) if resp_body_b64 else b""
    )

    return Response(content=resp_body, status_code=status, headers=resp_headers)


@router.websocket("/{session_id}/ws/{path:path}")
async def forward_ws(websocket: WebSocket, session_id: str, path: str):
    server_id = get_server_for_session(session_id)
    if server_id is None:
        await websocket.close(code=1008, reason="Session not found")
        return

    await websocket.accept()
    connection_id = str(uuid.uuid4())

    try:
        await send_proxy_ws_message(
            server_id,
            {
                "type": "ws_open",
                "connection_id": connection_id,
                "path": f"/{path}",
                "headers": dict(websocket.headers),
            },
        )

        register_ws_connection(connection_id, websocket)

        while True:
            msg = await websocket.receive()

            match msg["type"]:
                case "websocket.disconnect":
                    await send_proxy_ws_message(
                        server_id,
                        {
                            "type": "ws_close",
                            "connection_id": connection_id,
                            "code": msg.get("code", 1000),
                        },
                    )
                    break

                case "websocket.receive":
                    if msg.get("text") is not None:
                        opcode = "text"
                        data = msg["text"]
                    elif msg.get("bytes") is not None:
                        opcode = "binary"
                        data = base64.urlsafe_b64encode(msg["bytes"]).decode("ascii")
                    else:
                        continue

                    await send_proxy_ws_message(
                        server_id,
                        {
                            "type": "ws_frame",
                            "connection_id": connection_id,
                            "opcode": opcode,
                            "data": data,
                        },
                    )

    except RuntimeError as exc:
        # Failed to communicate with the backend proxy.
        if websocket.client_state.name == "CONNECTED":
            await websocket.close(code=1011, reason=str(exc))
    finally:
        unregister_ws_connection(connection_id)
