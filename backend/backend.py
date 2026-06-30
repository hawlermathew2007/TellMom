from fastapi import HTTPException

from adapters.base import ChatPlatform
from adapters.roblox import RobloxAdapter
from adapters.discord import DiscordAdapter
from adapters.minecraft import MinecraftAdapter
from cache import message_cache
from classifier_client import classifier_client
from models import FlaggedUser, IngestResponse

ADAPTER_MAP = {
    ChatPlatform.ROBLOX: RobloxAdapter,
    ChatPlatform.DISCORD: DiscordAdapter,
    ChatPlatform.MINECRAFT: MinecraftAdapter,
}

flag_store: dict[str, FlaggedUser] = {}


async def process_ingest(platform: str, chat_group: dict[str, list[str]]) -> IngestResponse:
    try:
        platform_enum = ChatPlatform(platform)
    except ValueError as exc:
        raise ValueError(f"Unknown platform: {platform}") from exc

    adapter_cls = ADAPTER_MAP[platform_enum]
    adapter = adapter_cls()
    normalized = adapter.normalize(chat_group)

    new_messages = message_cache.update(normalized)
    if not new_messages:
        return IngestResponse(
            status="no_new_messages",
            classified_count=0,
            newly_flagged=[],
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
        results = await classifier_client.classify(new_messages)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Classifier not connected. Retry later.",
        ) from exc

    newly_flagged: list[str] = []
    for result in results:
        if result.is_pedo:
            flag_store[result.user_id] = FlaggedUser(
                user_id=result.user_id,
                flagged_chats=message_cache.get_messages(result.user_id),
                resolved=False,
            )
            newly_flagged.append(result.user_id)

    return IngestResponse(
        status="ok",
        classified_count=len(results),
        newly_flagged=newly_flagged,
    )
