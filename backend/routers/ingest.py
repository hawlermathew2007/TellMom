from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.ingest import IngestRequest, IngestResponse
from services.ingest import process_ingest

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    try:
        return await process_ingest(
            db,
            request.platform,
            request.user_id,
            request.server_id,
            request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
