from fastapi import APIRouter, HTTPException

from backend import process_ingest
from models import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest) -> IngestResponse:
    try:
        return await process_ingest(request.platform, request.chat_group)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
