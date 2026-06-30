from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import process_ingest
from database.session import get_db
from models import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    try:
        return await process_ingest(
            db,
            request.platform,
            request.server_id,
            request.chat_group,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
