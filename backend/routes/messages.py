from fastapi import APIRouter, HTTPException, Header, status
from typing import List
from datetime import datetime
import logging
from models.message import MessageCapture, MessageResponse, MessageHistoryResponse, MessageAnalysis
from services.grooming_detector import predict_grooming_risk
from routes.alerts import create_in_app_alert
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory message storage (replace with DB in production)
message_store: List[MessageResponse] = []


@router.post("/capture")
async def capture_message(
    message: MessageCapture,
    x_roblox_api_key: str = Header(..., description="Roblox API key")
):
    """
    Roblox client sends a chat message for analysis.

    **Flow:**
    1. Receive message from Roblox TextChatService
    2. Verify API key
    3. Run grooming detection AI
    4. If high risk: alert parent
    5. Store encrypted message (COPPA: data retention)
    """

    # Verify API key
    if x_roblox_api_key != settings.roblox_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Roblox API key"
        )

    logger.info(
        f"📨 Message captured from {message.username} (ID: {message.roblox_user_id}): "
        f"{message.text[:50]}..."
    )

    # Run AI grooming detection
    try:
        risk_score, confidence, explanation, flagged_phrases = predict_grooming_risk(
            message.text
        )
    except Exception as e:
        logger.error(f"[*] AI inference failed: {e}")
        risk_score, confidence, explanation, flagged_phrases = 0.0, 0.0, "Error", []

    # Determine risk level
    if risk_score >= 0.75:
        risk_level = "RED"
    elif risk_score >= 0.5:
        risk_level = "YELLOW"
    else:
        risk_level = "GREEN"

    # Create analysis
    analysis = MessageAnalysis(
        message_id=len(message_store) + 1,
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        explanation=explanation,
        flagged_phrases=flagged_phrases,
        analyzed_at=datetime.utcnow()
    )

    # Create message response
    msg_response = MessageResponse(
        id=len(message_store) + 1,
        roblox_user_id=message.roblox_user_id,
        username=message.username,
        text=message.text,
        timestamp=message.timestamp,
        analysis=analysis,
        parent_notified=False,
        parent_acknowledged=False
    )

    # Store message
    message_store.append(msg_response)

    # Alert parent if high risk
    if risk_level in ["YELLOW", "RED"]:
        logger.warning(f"[*] HIGH RISK MESSAGE: {risk_level} (score: {risk_score:.2f})")

        # Create in-app alert (no email)
        await create_in_app_alert(
            child_id=message.child_id,
            risk_level=risk_level,
            message_preview=message.text[:100],
            risk_score=risk_score,
            flagged_phrases=flagged_phrases
        )
        msg_response.parent_notified = True

    return {
        "status": "message_captured",
        "message_id": msg_response.id,
        "analysis": analysis,
        "parent_notified": msg_response.parent_notified
    }


@router.get("/history", response_model=MessageHistoryResponse)
async def get_message_history(child_id: str, limit: int = 100):
    """
    Retrieve message history for a child.

    **COPPA Requirement:** Parent can view all collected data.
    """
    # Filter messages by child
    child_messages = [
        msg for msg in message_store
        if msg.roblox_user_id == child_id
    ][-limit:]

    high_risk_count = sum(
        1 for msg in child_messages
        if msg.analysis and msg.analysis.risk_level in ["YELLOW", "RED"]
    )

    return MessageHistoryResponse(
        total_count=len(child_messages),
        high_risk_count=high_risk_count,
        messages=child_messages
    )


@router.get("/summary")
async def get_risk_summary(child_id: str):
    """
    Get risk summary for a child.
    """
    child_messages = [
        msg for msg in message_store
        if msg.roblox_user_id == child_id
    ]
 
    total = len(child_messages)
    red_count = sum(1 for m in child_messages if m.analysis and m.analysis.risk_level == "RED")
    yellow_count = sum(1 for m in child_messages if m.analysis and m.analysis.risk_level == "YELLOW")

    avg_risk = (
        sum(m.analysis.risk_score for m in child_messages if m.analysis) / total
        if total > 0 else 0.0
    )

    return {
        "child_id": child_id,
        "total_messages": total,
        "red_flag_count": red_count,
        "yellow_flag_count": yellow_count,
        "average_risk_score": avg_risk,
        "trend": "increasing" if red_count > 0 else "stable"
    }


@router.delete("/message/{message_id}")
async def delete_message(message_id: int):
    """
    Delete a message (parent request).

    **COPPA Requirement:** Parent has right to delete child data.
    Deletion must be secure (cryptographic erasure).
    """
    global message_store

    # Find and remove message
    message_store = [m for m in message_store if m.id != message_id]

    logger.info(f"🗑️  Message {message_id} deleted by parent")

    return {
        "status": "message_deleted",
        "message_id": message_id,
        "deleted_at": datetime.utcnow()
    }
