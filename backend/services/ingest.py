import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session

from adapters.base import ChatPlatform
from core import config
from core.cache import message_cache
from core.classifier_client import classifier_client
from services.classifier_stream import classifier_stream
from database.models import ChildAccount
from schemas.flags import FlaggedConversation
from services.explanation import get_or_generate_explanation
from services.messages import add_message_db, notify_parents_in_chat, load_server_chat_group

flag_store: dict[str, FlaggedConversation] = {}
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

    # Add message to cache / db
    message_cache.add(platform, server_id, user_id, message)
    add_message_db(db, platform, server_id, user_id, message)

    message_count = message_cache.count_server_messages(platform, server_id)

    # TODO: what is this even for ?
    if message_count < config.CLASSIFIER_MIN_MESSAGES:
        return

    messages = message_cache.get_server_entries(platform, server_id)
    raw =  " ".join([m.message for m in messages]) 

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

        flagged_messages = [m.message for m in messages]
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
