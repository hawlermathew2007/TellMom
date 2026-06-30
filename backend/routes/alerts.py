from fastapi import APIRouter, HTTPException, WebSocket
from typing import List, Dict
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory alert store
alert_store: Dict[str, List[dict]] = {}  # child_id -> [alerts]
active_connections: List[WebSocket] = []  # Active WebSocket connections


class Alert:
    def __init__(self, child_id: str, risk_level: str, message_preview: str, risk_score: float, flagged_phrases: List[str]):
        self.id = len(alert_store.get(child_id, [])) + 1
        self.child_id = child_id
        self.risk_level = risk_level
        self.message_preview = message_preview
        self.risk_score = risk_score
        self.flagged_phrases = flagged_phrases
        self.triggered_at = datetime.utcnow().isoformat()
        self.acknowledged = False
        self.acknowledged_at = None


@router.post("/trigger")
async def trigger_alert(child_id: str, risk_level: str, message: str, risk_score: float, flagged_phrases: List[str] = []):
    """
    Create an in-app alert (no email).
    Immediately broadcast to all connected WebSocket clients.
    """
    alert_dict = {
        "id": len(alert_store.get(child_id, [])) + 1,
        "child_id": child_id,
        "risk_level": risk_level,
        "message_preview": message[:100],
        "risk_score": risk_score,
        "flagged_phrases": flagged_phrases,
        "triggered_at": datetime.utcnow().isoformat(),
        "acknowledged": False,
    }

    # Store alert
    if child_id not in alert_store:
        alert_store[child_id] = []
    alert_store[child_id].append(alert_dict)

    logger.warning(f"🚨 Alert triggered: {risk_level} for child {child_id}")

    # Broadcast to all connected clients
    await broadcast_alert(alert_dict)

    return {
        "alert_id": alert_dict["id"],
        "status": "alert_created",
        "risk_level": risk_level,
        "timestamp": alert_dict["triggered_at"]
    }


@router.get("/history")
async def get_alert_history(child_id: str, limit: int = 50):
    """
    Get alert history for a child.
    """
    alerts = alert_store.get(child_id, [])
    alerts = sorted(alerts, key=lambda x: x["triggered_at"], reverse=True)[:limit]

    return {
        "total_alerts": len(alerts),
        "alerts": alerts
    }


@router.post("/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: int, child_id: str):
    """
    Parent acknowledges an alert on the dashboard.
    """
    if child_id not in alert_store:
        raise HTTPException(status_code=404, detail="No alerts for this child")

    for alert in alert_store[child_id]:
        if alert["id"] == alert_id:
            alert["acknowledged"] = True
            alert["acknowledged_at"] = datetime.utcnow().isoformat()
            logger.info(f"[+] Alert {alert_id} acknowledged")
            return {"status": "alert_acknowledged", "alert_id": alert_id}

    raise HTTPException(status_code=404, detail="Alert not found")


# WebSocket for real-time alerts
@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alert streaming to dashboard.
    """
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("[+] WebSocket connected for real-time alerts")

    try:
        while True:
            # Keep connection alive and wait for messages
            data = await websocket.receive_text()
            # Can handle client messages here if needed
    except Exception as e:
        logger.error(f"[+] WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)
        logger.info("[*] WebSocket disconnected")


async def broadcast_alert(alert_dict: dict):
    """
    Send alert to all connected WebSocket clients.
    """
    for connection in active_connections:
        try:
            await connection.send_json({
                "type": "alert",
                "data": alert_dict
            })
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")


async def create_in_app_alert(
    child_id: str,
    risk_level: str,
    message_preview: str,
    risk_score: float,
    flagged_phrases: List[str]
):
    """
    Create in-app alert instead of sending email.
    """
    await trigger_alert(
        child_id=child_id,
        risk_level=risk_level,
        message=message_preview,
        risk_score=risk_score,
        flagged_phrases=flagged_phrases
    )
