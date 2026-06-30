from fastapi import APIRouter, Query

from backend import flag_store
from models import FlaggedUser

router = APIRouter()


@router.get("/flags", response_model=list[FlaggedUser])
async def list_flags(resolved: bool | None = Query(default=None)) -> list[FlaggedUser]:
    flags = list(flag_store.values())
    if resolved is False:
        flags = [f for f in flags if not f.resolved]
    elif resolved is True:
        flags = [f for f in flags if f.resolved]
    return flags
