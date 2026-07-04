from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session
import json

from core import config
from database.session import get_db
from schemas.ingest import (
    ClassifierCheckInRequest,
    ClassifierCheckInResponse,
    IngestRequest,
)
from services.classifier_stream import classifier_stream
from services.ingest import process_ingest
from services.stream_security import create_stream_token, decode_stream_token

router = APIRouter()
classifier_router = APIRouter(tags=["classifier"])


@router.post("/ingest", status_code=204)
async def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> None:
    try:
        await process_ingest(
            db,
            request.platform,
            request.user_id,
            request.server_id,
            request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@classifier_router.post("/checkin", response_model=ClassifierCheckInResponse)
async def classifier_checkin(
    _: ClassifierCheckInRequest,
    x_password: str | None = Header(default=None, alias="X-Password"),
) -> ClassifierCheckInResponse:
    if x_password != config.CLASSIFIER_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid classifier password")
    token = create_stream_token()
    return ClassifierCheckInResponse(token=token)


@classifier_router.websocket("/stream")
async def learner_stream(websocket: WebSocket) -> None:
    await websocket.accept()

    # Use first message as "auth header" instead
    # First method did not work bcuz WebSocket actually did not let us modify the Header
    # Available Header is Sec-Websocket-Protocol which is not for holding JWT. So kinda diabolic if tryna git push --force
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
