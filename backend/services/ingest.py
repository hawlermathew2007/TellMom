import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from services.classifier_stream import classifier_stream
from sqlalchemy.orm import Session

from core.registry import ChatPlatform
from core import config
from database.models import ChatMessage

from services.explanation import increment_unprocessed_count
from services.messages import (
    add_message_db,
    notify_parents_in_chat,
    load_server_chat_group,
    count_server_messages,
)

logger = logging.getLogger(__name__)


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
    message_count = count_server_messages(
        db, platform, server_id, max_age_hours=config.MESSAGE_CACHE_TTL_HOURS
    )

    if message_count < config.CLASSIFIER_MIN_MESSAGES:
        return

    # Load messages of conversation from DB within the TTL timeframe
    since = datetime.now(timezone.utc) - timedelta(hours=config.MESSAGE_CACHE_TTL_HOURS)
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
        await classifier_stream.ensure_connected()
        result = await classifier_stream.classify(raw)
    except ConnectionError as e:
        logger.error(e)
        raise HTTPException(
            status_code=503,
            detail=f"Classifier not connected. Retry later. {e}",
        )

    logger.warning(f"Classification result: {result.has_pedo} (probability: {result.probability})")
    if result.has_pedo:
        chat_group = load_server_chat_group(
            db, platform, server_id, max_age_hours=config.MESSAGE_CACHE_TTL_HOURS
        )

        # Start incremental grooming analysis by tracking unprocessed messages
        increment_unprocessed_count(db, platform, server_id)
        preview = (
            db_messages[-1].content if db_messages else "suspicious message deteceted"
        )
        await notify_parents_in_chat(
            db,
            platform,
            server_id,
            chat_group,
            preview,
            result.probability,
        )
