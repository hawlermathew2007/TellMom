import logging
from datetime import datetime
from dataclasses import dataclass
from database.models import ChildAccount
from fastapi import HTTPException
from services.classifier_stream import classifier_stream
from sqlalchemy.orm import Session
from collections import defaultdict

from core.registry import ChatPlatform
from core import config

from services.explanation import increment_unprocessed_count
from services.messages import (
    add_message_db,
    notify_parent,
)
from core.cache import message_cache, sync_message_cache

logger = logging.getLogger(__name__)


@dataclass
class MessageCacheItem:
    id: str
    user_id: str
    platform: ChatPlatform
    server_id: str
    user_id: str
    content: str
    created_at: datetime


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

    # Add message to db / cache layer
    msg = add_message_db(db, platform, server_id, user_id, message)

    # Load messages of conversation from cache / DB if expired
    sync_message_cache(db, platform, server_id)
    cache = message_cache.get(server_id)
    assert cache is not None

    # convert to built-in data type for cache storage
    msg = MessageCacheItem(
        **{col.name: getattr(msg, col.name) for col in msg.__table__.columns}
    )
    cache["collection"].append(msg)
    cache["map"][msg.user_id].append(msg)
    messages = cache["collection"]

    id_to_chats = defaultdict(list)
    for msg in messages:
        id_to_chats[msg.user_id].append(msg)

    children = db.query(ChildAccount).all()
    for child in children:
        child_id = child.platform_user_id
        child_messages = id_to_chats.get(child_id)
        if child_messages is None:
            continue

        for k, v in id_to_chats.items():
            if k == child_id:
                continue

            if len(v) + len(child_messages) < config.CLASSIFIER_MIN_MESSAGES:
                continue

            conversation = v + child_messages
            conversation.sort(key=lambda x: x.created_at)
            raw = " ".join([m.content for m in conversation])

            try:
                await classifier_stream.ensure_connected()
                result = await classifier_stream.classify(raw)
            except ConnectionError as e:
                logger.error(e)
                raise HTTPException(
                    status_code=503,
                    detail=f"Classifier not connected. Retry later. {e}",
                )

            # For debugging only
            logger.warning(
                f"Classification result: {bool(result.has_pedo)}"
                f"Probability: {float(result.probability)}"
            )

            if not result.has_pedo:
                continue

            # NOTE: doing this to avoid maintaining the read state in both db and cache
            preview = (
                messages[-1].content if messages else "suspicious message deteceted"
            )
            alert = await notify_parent(
                db=db,
                platform=platform,
                child=child,
                target_id=k,
                server_id=server_id,
                preview=preview,
                probability=result.probability,
                messages=conversation,
            )

            increment_unprocessed_count(db, str(alert.id))
