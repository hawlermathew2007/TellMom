from fastapi import HTTPException
from sqlalchemy.orm import Session

from adapters.base import ChatPlatform
from core import config
from core.cache import message_cache
from core.classifier_client import classifier_client
from services.classifier_stream import classifier_stream
from database.models import ChildAccount
from schemas.flags import FlaggedUser
from schemas.ingest import IngestResponse
from services.explanation import get_or_generate_explanation
from services.messages import notify_parents_in_chat, persist_chat_message

flag_store: dict[str, FlaggedUser] = {}


async def process_ingest(
    db: Session,
    platform: str,
    user_id: str,
    server_id: str,
    message: str,
) -> IngestResponse:
    try:
        platform_enum = ChatPlatform(platform)
    except ValueError as exc:
        raise ValueError(f"Unknown platform: {platform}") from exc

    message_cache.add(platform, server_id, user_id, message)
    persist_chat_message(db, platform_enum, server_id, user_id, message)

    message_count = message_cache.count_server_messages(platform, server_id)

    if message_count < config.CLASSIFIER_MIN_MESSAGES:
        return IngestResponse(
            status="below_threshold",
            message_count=message_count,
            classified_count=0,
            newly_flagged=[],
            parents_notified=0,
        )

    chat_group = message_cache.load_server_chat_group(platform, server_id)

    try:
        if classifier_stream.connected:
            results = await classifier_stream.classify(platform, server_id, chat_group)
        else:
            await classifier_client.ensure_connected()
            results = await classifier_client.classify(platform, server_id, chat_group)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Classifier not connected. Retry later.",
        ) from exc

    newly_flagged: list[str] = []
    parents_notified = 0

    for result in results:
        if result.is_pedo:
            flagged_messages = chat_group.get(result.user_id, [])
            explanation = await get_or_generate_explanation(
                db,
                platform_enum,
                result.user_id,
                server_id,
                chat_group,
            )
            explanation_payload = (
                explanation.model_dump(mode="json") if explanation is not None else None
            )
            flag_store[result.user_id] = FlaggedUser(
                user_id=result.user_id,
                server_id=server_id,
                platform=platform,
                flagged_chats=flagged_messages,
                resolved=False,
                explanation=explanation,
            )
            newly_flagged.append(result.user_id)

            children_before = (
                db.query(ChildAccount)
                .filter(
                    ChildAccount.platform == platform_enum,
                    ChildAccount.platform_user_id.in_(set(chat_group.keys())),
                )
                .count()
            )
            await notify_parents_in_chat(
                db,
                platform_enum,
                server_id,
                chat_group,
                result.user_id,
                flagged_messages,
                explanation_payload,
            )
            parents_notified += children_before

    return IngestResponse(
        status="classified",
        message_count=message_count,
        classified_count=len(results),
        newly_flagged=newly_flagged,
        parents_notified=parents_notified,
    )
