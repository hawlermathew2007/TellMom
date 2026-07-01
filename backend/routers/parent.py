from fastapi import APIRouter, HTTPException

from core.cache import flag_store

router = APIRouter()


@router.post("/flags/{platform}/{server_id}/resolve")
async def resolve_flag(platform: str, server_id: str) -> dict:
    flag_key = f"{platform}:{server_id}"
    if flag_key not in flag_store:
        raise HTTPException(status_code=404, detail=f"Flag not found for key: {flag_key}")

    flag_store[flag_key].resolved = True
    return {"status": "resolved", "platform": platform, "server_id": server_id}
