from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from core import config
from database.session import get_db
from schemas.ingest import (
    ClassifierCheckInRequest,
    ClassifierCheckInResponse,
    IngestRequest,
)
from services.classifier_stream import classifier_stream
from services.ingest import process_ingest

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
    return ClassifierCheckInResponse()


# TODO: rename this one
@classifier_router.websocket("/stream")
async def learner_stream(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if token != config.CLASSIFIER_PASSWORD:
        await websocket.close(code=4401)
        return

    await classifier_stream.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            classifier_stream.handle_message(raw)
    except WebSocketDisconnect:
        classifier_stream.disconnect()
