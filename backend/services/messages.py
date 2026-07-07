from sqlalchemy.orm import Session

from core.registry import ChatPlatform
from database.models import Alert, ChatMessage, ChildAccount, IncrementalAnalysis
from schemas.alerts import AlertResponse, ChatMessageResponse
from services.notifications import alert_manager


def add_message_db(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    user_id: str,
    message: str,
) -> ChatMessage:
    msg = ChatMessage(
        platform=platform,
        server_id=server_id,
        user_id=user_id,
        content=message,
    )
    db.add(msg)
    db.commit()
    return msg


def count_server_messages(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
) -> int:
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == platform,
            ChatMessage.server_id == server_id,
        )
        .count()
    )


def get_server_messages(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == platform,
            ChatMessage.server_id == server_id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


async def notify_parent(
    *,
    db: Session,
    platform: ChatPlatform,
    child: ChildAccount,
    target_id: str,
    server_id: str,
    preview: str,
    probability: float,
    messages: list[ChatMessage],
) -> Alert:
    alert = _upsert_alert(
        db=db,
        child=child,
        target_id=target_id,
        platform=platform,
        server_id=server_id,
        preview=preview,
        probability=probability,
    )
    # NOTE: force alchemy to populate alert.id (not done for new entries)
    db.flush()
    _upsert_analysis(db=db, alert_id=str(alert.id), unprocessed_count=len(messages))
    db.commit()
    await _send_alert_notification(db, alert, messages)
    return alert


def _upsert_analysis(
    *, db: Session, alert_id: str, unprocessed_count: int
) -> IncrementalAnalysis:
    record = (
        db.query(IncrementalAnalysis)
        .filter(IncrementalAnalysis.alert_id == alert_id)
        .first()
    )

    if record is None:
        record = IncrementalAnalysis(
            alert_id=alert_id,
            detected_stages=[],
            unprocessed_message_count=unprocessed_count,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return record


def _upsert_alert(
    *,
    db: Session,
    child: ChildAccount,
    target_id: str,
    platform: ChatPlatform,
    server_id: str,
    preview: str,
    probability: float,
) -> Alert:
    """Create a new alert for flagged child, or update it if one already exists for this server conversation."""
    alert = (
        db.query(Alert)
        .filter(
            Alert.platform == platform,
            Alert.server_id == server_id,
            Alert.child_account_id == child.id,
            Alert.target_id == target_id,
        )
        .one_or_none()
    )

    if alert:
        alert.message_preview = preview[:500]
        alert.probability = probability
        alert.is_read = False
    else:
        alert = Alert(
            parent_id=child.parent_id,
            child_account_id=child.id,
            target_id=target_id,
            platform=platform,
            server_id=server_id,
            message_preview=preview[:500],
            probability=probability,
        )
        db.add(alert)
    return alert


async def _send_alert_notification(
    db: Session, alert: Alert, messages: list[ChatMessage]
) -> None:
    db.refresh(alert)

    alert_res = AlertResponse.model_validate(alert)
    alert_res.messages = [ChatMessageResponse.model_validate(m) for m in messages]

    payload = alert_res.model_dump(mode="json")
    payload["type"] = "alert"

    await alert_manager.notify_parent(alert.parent_id, payload)
