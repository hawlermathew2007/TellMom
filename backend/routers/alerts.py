from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database.models import Alert, Parent
from database.session import SessionLocal, get_db
from dependencies import get_current_parent
from schemas.alerts import AlertResponse
from services.auth import get_parent_from_token
from services.notifications import alert_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[Alert]:
    return (
        db.query(Alert)
        .filter(Alert.parent_id == parent.id)
        .order_by(Alert.created_at.desc())
        .all()
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> Alert:
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
    return alert


@router.websocket("/ws")
async def alerts_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

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
