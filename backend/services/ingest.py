import logging
from datetime import UTC, datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from adapters.base import ChatPlatform
from core import config
from core.cache import flag_store
from core.classifier_client import classifier_client
from services.classifier_stream import classifier_stream
from database.models import ChatMessage
from schemas.flags import FlaggedConversation
from services.explanation import get_or_generate_explanation
from services.messages import add_message_db, notify_parents_in_chat, load_server_chat_group, count_server_messages

logger = logging.getLogger()


async def process_ingest(
    db: Session,
    platform: ChatPlatform,
    user_id: str,
    server_id: str,
    message: str,
) -> None:
    """
    Store ingest into cache and db then perform classification
    if all pre-defined requirements are met.
    """

    # Add message to db
    add_message_db(db, platform, server_id, user_id, message)

    message_count = count_server_messages(db, platform, server_id, max_age_hours=config.MESSAGE_CACHE_TTL_HOURS)

    if message_count < config.CLASSIFIER_MIN_MESSAGES:
        return

    # Load messages of conversation from DB within the TTL timeframe
    since = datetime.now(UTC) - timedelta(hours=config.MESSAGE_CACHE_TTL_HOURS)
    db_messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.platform == platform,
            ChatMessage.server_id == server_id,
            ChatMessage.created_at >= since,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    raw = " ".join([m.content for m in db_messages])

    try:
        if not classifier_stream.connected:
            await classifier_client.ensure_connected()
        result = await classifier_client.classify(raw)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Classifier not connected. Retry later.",
        ) from exc

    if result.has_pedo:
        chat_group = load_server_chat_group(db, platform, server_id, max_age_hours=config.MESSAGE_CACHE_TTL_HOURS)
        explanation = await get_or_generate_explanation(db, platform, server_id, chat_group)
        explanation_payload = explanation.model_dump(mode="json") if explanation else None

        flagged_messages = [m.content for m in db_messages]
        flag_key = f"{platform.value}:{server_id}"
        flag_store[flag_key] = FlaggedConversation(
            platform=platform.value,
            server_id=server_id,
            flagged_chats=flagged_messages,
            resolved=False,
            explanation=explanation,
        )

        await notify_parents_in_chat(
            db,
            platform,
            server_id,
            chat_group,
            flagged_messages,
            explanation_payload,
        )
