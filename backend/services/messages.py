from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.registry import ChatPlatform
from database.models import Alert, ChatMessage, ChildAccount
from schemas.alerts import AlertResponse, ChatMessageResponse
from services.notifications import alert_manager


def add_message_db(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    user_id: str,
    message: str,
) -> None:
    db.add(
        ChatMessage(
            platform=platform,
            server_id=server_id,
            sender_platform_user_id=user_id,
            content=message,
        )
    )
    db.commit()


def load_server_chat_group(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    *,
    max_age_hours: int,
) -> dict[str, list[str]]:
    since = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == platform,
            ChatMessage.server_id == server_id,
            ChatMessage.created_at >= since,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    chat_group: dict[str, list[str]] = {}
    for row in rows:
        chat_group.setdefault(row.sender_platform_user_id, []).append(row.content)
    return chat_group


def count_server_messages(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    *,
    max_age_hours: int,
) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == platform,
            ChatMessage.server_id == server_id,
            ChatMessage.created_at >= since,
        )
        .count()
    )


async def notify_parents_in_chat(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    chat_group: dict[str, list[str]],
    preview: str,
    probability: float,
) -> None:
    participant_ids = set(chat_group.keys())
    children = (
        db.query(ChildAccount)
        .filter(
            ChildAccount.platform == platform,
            ChildAccount.platform_user_id.in_(participant_ids),
        )
        .all()
    )
    if not children:
        return

    parent_ids: set[int] = set()
    created_alerts: list[Alert] = []

    # Check for recent alerts to avoid duplicates
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_alerts = (
        db.query(Alert)
        .filter(
            Alert.platform == platform,
            Alert.server_id == server_id,
            Alert.created_at >= since,
        )
        .all()
    )
    recent_child_ids = {alert.child_account_id for alert in recent_alerts}

    for child in children:
        # Skip if alert already exists for this child in this server within past hour
        if child.id in recent_child_ids:
            continue

        alert = Alert(
            parent_id=child.parent_id,
            child_account_id=child.id,
            platform=platform,
            server_id=server_id,
            message_preview=preview[:500],
            probability=probability,
        )
        db.add(alert)
        created_alerts.append(alert)
        parent_ids.add(child.parent_id)

    db.commit()

    for alert in created_alerts:
        db.refresh(alert)
        # Fetch conversation messages to link them together
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
        payload = alert_res.model_dump(mode="json")
        payload["type"] = "alert"
        await alert_manager.notify_parent(alert.parent_id, payload)
