from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.schemas.ingest import IngestRequest
from backend.services.ingest import process_ingest

router = APIRouter(prefix="/message", tags=["message"])


# TODO: make sure the ingest processing can decrypt the message and such
@router.post("/ingest", status_code=204)
async def ingest(request: IngestRequest, db: Session = Depends(get_db)) -> None:
    try:
        await process_ingest(
            db,
            request.platform,
            request.user_id,
            request.server_id,
            request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
