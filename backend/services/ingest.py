from fastapi import HTTPException
from sqlalchemy.orm import Session

from adapters.base import ChatPlatform
from adapters.discord import DiscordAdapter
from adapters.minecraft import MinecraftAdapter
from adapters.roblox import RobloxAdapter
from core.cache import message_cache
from core.classifier_client import classifier_client
from database.models import ChildAccount
from schemas.flags import FlaggedUser
from schemas.ingest import IngestResponse
from services.messages import notify_parents_in_chat, persist_chat_messages

ADAPTER_MAP = {
    ChatPlatform.ROBLOX: RobloxAdapter,
    ChatPlatform.DISCORD: DiscordAdapter,
    ChatPlatform.MINECRAFT: MinecraftAdapter,
}

flag_store: dict[str, FlaggedUser] = {}


async def process_ingest(
    db: Session,
    platform: str,
    server_id: str,
    chat_group: dict[str, list[str]],
) -> IngestResponse:
    try:
        platform_enum = ChatPlatform(platform)
    except ValueError as exc:
        raise ValueError(f"Unknown platform: {platform}") from exc

    adapter_cls = ADAPTER_MAP[platform_enum]
    adapter = adapter_cls()
    normalized = adapter.normalize(chat_group)

    new_messages = message_cache.update(normalized)
    if new_messages:
        persist_chat_messages(db, platform_enum, server_id, new_messages)

    if not new_messages:
        return IngestResponse(
            status="no_new_messages",
            classified_count=0,
            newly_flagged=[],
            parents_notified=0,
        )

    try:
        await classifier_client.ensure_connected()
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Classifier not connected. Retry later.",
        ) from exc

    if not classifier_client.connected:
        raise HTTPException(
            status_code=503,
            detail="Classifier not connected. Retry later.",
        )

    try:
        results = await classifier_client.classify(platform, server_id, new_messages)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Classifier not connected. Retry later.",
        ) from exc

    newly_flagged: list[str] = []
    parents_notified = 0

    for result in results:
        if result.is_pedo:
            flagged_messages = message_cache.get_messages(result.user_id)
            flag_store[result.user_id] = FlaggedUser(
                user_id=result.user_id,
                server_id=server_id,
                platform=platform,
                flagged_chats=flagged_messages,
                resolved=False,
            )
            newly_flagged.append(result.user_id)

            children_before = (
                db.query(ChildAccount)
                .filter(
                    ChildAccount.platform == platform_enum,
                    ChildAccount.platform_user_id.in_(set(normalized.keys())),
                )
                .count()
            )
            await notify_parents_in_chat(
                db,
                platform_enum,
                server_id,
                normalized,
                result.user_id,
                flagged_messages,
            )
            parents_notified += children_before

    return IngestResponse(
        status="ok",
        classified_count=len(results),
        newly_flagged=newly_flagged,
        parents_notified=parents_notified,
    )
