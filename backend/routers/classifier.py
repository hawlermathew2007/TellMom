import json
from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from backend.core import config
from backend.schemas.ingest import (
    ClassifierCheckInRequest,
    ClassifierCheckInResponse,
)
from backend.services.classifier_stream import classifier_stream
from backend.core.jwt import create_stream_token, decode_stream_token
from shared.schemas.response import ResponseStatus

router = APIRouter(prefix="/classifier", tags=["classifier"])


@router.post("/checkin", response_model=ClassifierCheckInResponse)
async def classifier_checkin(
    _: ClassifierCheckInRequest,
    x_password: str | None = Header(default=None, alias="X-Password"),
) -> ClassifierCheckInResponse:
    if x_password != config.CLASSIFIER_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid classifier password")
    token = create_stream_token()
    return ClassifierCheckInResponse(token=token, status=ResponseStatus.SUCCESS)


@router.websocket("/stream")
async def learner_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        first_message = await websocket.receive_text()
        payload = json.loads(first_message)
        if payload.get("type") != "auth":
            raise ValueError("First message must be of type 'auth'")
        token = payload["token"]
    except (json.JSONDecodeError, KeyError, ValueError):
        await websocket.close(code=4400, reason="Broken auth message.")
        return

    try:
        _ = decode_stream_token(token)
    except HTTPException:
        await websocket.close(code=4401, reason="Invalid token")
        return

    # Let the server know that authentication done
    await websocket.send_text(json.dumps({"type": "auth_ok"}))

    # Start WS
    await classifier_stream.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            classifier_stream.handle_message(raw)
    except WebSocketDisconnect:
        classifier_stream.disconnect()
