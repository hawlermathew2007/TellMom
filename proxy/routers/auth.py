import logging
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session

from proxy.core.jwt import create_stream_token
from proxy.core.security import hash_password, verify_password
from proxy.database.session import get_db
from proxy.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    ServerTokenResponse,
)
from proxy.database.models import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ServerTokenResponse)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> ServerTokenResponse:
    existing = db.query(Server).filter(Server.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already registered")

    server = Server(username=body.username, password_hash=hash_password(body.password))
    db.add(server)
    db.commit()
    db.refresh(server)

    return ServerTokenResponse(
        access_token=create_stream_token(str(server.id)),
        server_id=str(server.id),
    )


@router.post("/login", response_model=ServerTokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> ServerTokenResponse:
    server = db.query(Server).filter(Server.username == body.username).first()
    if server is None or not verify_password(body.password, server.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return ServerTokenResponse(
        access_token=create_stream_token(str(server.id)),
        server_id=str(server.id),
    )
