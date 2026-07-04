from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json

from database.models import Alert, Parent, ChatMessage
from database.session import SessionLocal, get_db
from core.dependencies import get_current_parent
from schemas.alerts import AlertResponse, ChatMessageResponse
from schemas.grooming import IncrementalAnalysisResponse
from services.auth import get_parent_from_token
from services.notifications import alert_manager
from services.explanation import get_incremental_analysis
from services.stream_security import decode_stream_token
from core.registry import ChatPlatform

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    alerts = (
        db.query(Alert)
        .filter(Alert.parent_id == parent.id)
        .order_by(Alert.created_at.desc())
        .all()
    )
    response = []
    for alert in alerts:
        messages = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.platform == alert.platform,
                ChatMessage.server_id == alert.server_id,
            )
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        alert_res = AlertResponse.model_validate(alert)
        alert_res.messages = [ChatMessageResponse.model_validate(m) for m in messages]
        response.append(alert_res)
    return response


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.parent_id == parent.id)
        .first()
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    db.commit()
    db.refresh(alert)

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == alert.platform,
            ChatMessage.server_id == alert.server_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    alert_res = AlertResponse.model_validate(alert)
    alert_res.messages = [ChatMessageResponse.model_validate(m) for m in messages]
    return alert_res


@router.get("/{alert_id}/grooming-analysis", response_model=IncrementalAnalysisResponse)
async def get_grooming_analysis(
    alert_id: int,
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> IncrementalAnalysisResponse:
    """
    Get or generate incremental grooming analysis for an alert.

    Returns only newly detected stages (empty if none detected or already fully analyzed).
    """
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.parent_id == parent.id)
        .first()
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Parse platform from alert
    try:
        platform = ChatPlatform(
            alert.platform.value if hasattr(alert.platform, "value") else alert.platform
        )
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid platform in alert")

    # Get incremental analysis
    result = await get_incremental_analysis(db, platform, alert.server_id)

    if result is None:
        # Analysis failed or threshold not met
        return IncrementalAnalysisResponse(new_stages=[])

    return result


@router.websocket("/ws")
async def alerts_websocket(websocket: WebSocket) -> None:
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
        await websocket.close(code=4401)
        return

    # Let the server know that authentication done
    await websocket.send_text(json.dumps({"type": "auth_ok"}))

    # Start WS
    db = SessionLocal()
    try:
        parent = get_parent_from_token(db, token)
        if parent is None:
            await websocket.close(code=4401)
            return

        await alert_manager.connect(parent.id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            alert_manager.disconnect(parent.id, websocket)
    finally:
        db.close()
