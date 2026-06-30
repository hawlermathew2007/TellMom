from fastapi import APIRouter, HTTPException

from services.ingest import flag_store

router = APIRouter()


@router.post("/flags/{user_id}/resolve")
async def resolve_flag(user_id: str) -> dict:
    if user_id not in flag_store:
        raise HTTPException(status_code=404, detail=f"Flag not found for user: {user_id}")

    flag_store[user_id].resolved = True
    return {"status": "resolved", "user_id": user_id}
