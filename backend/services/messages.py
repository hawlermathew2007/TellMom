from sqlalchemy.orm import Session

from adapters.base import ChatPlatform
from database.models import Alert, ChatMessage, ChildAccount
from schemas.alerts import AlertResponse
from services.notifications import alert_manager


def persist_chat_messages(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    chat_group: dict[str, list[str]],
) -> None:
    for sender_id, messages in chat_group.items():
        for content in messages:
            db.add(
                ChatMessage(
                    platform=platform,
                    server_id=server_id,
                    sender_platform_user_id=sender_id,
                    content=content,
                )
            )
    db.commit()


async def notify_parents_in_chat(
    db: Session,
    platform: ChatPlatform,
    server_id: str,
    chat_group: dict[str, list[str]],
    flagged_user_id: str,
    flagged_messages: list[str],
    explanation: dict | None = None,
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

    preview = flagged_messages[-1] if flagged_messages else "Suspicious activity detected"
    parent_ids: set[int] = set()
    created_alerts: list[Alert] = []

    for child in children:
        alert = Alert(
            parent_id=child.parent_id,
            child_account_id=child.id,
            flagged_user_id=flagged_user_id,
            platform=platform,
            server_id=server_id,
            message_preview=preview[:500],
            explanation=explanation,
        )
        db.add(alert)
        created_alerts.append(alert)
        parent_ids.add(child.parent_id)

    db.commit()

    for alert in created_alerts:
        db.refresh(alert)
        payload = AlertResponse.model_validate(alert).model_dump(mode="json")
        payload["type"] = "alert"
        await alert_manager.notify_parent(alert.parent_id, payload)
