from fastapi import APIRouter, Query

from schemas.flags import FlaggedConversation
from core.cache import flag_store

router = APIRouter()


@router.get("/flags", response_model=list[FlaggedConversation])
async def list_flags(resolved: bool | None = Query(default=None)) -> list[FlaggedConversation]:
    flags = list(flag_store.values())
    if resolved is False:
        flags = [f for f in flags if not f.resolved]
    elif resolved is True:
        flags = [f for f in flags if f.resolved]
    return flags
