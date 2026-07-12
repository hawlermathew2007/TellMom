import logging
from fastapi import Depends, APIRouter, HTTPException, WebSocket
from sqlalchemy.orm import Session

from proxy.core.jwt import create_stream_token
from proxy.core.security import hash_password, verify_password
from proxy.database.session import get_db
from proxy.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from proxy.database.models import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_map: dict[str, WebSocket] = {}
router = APIRouter()


@router.post("/register")
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> None:
    existing = db.query(Server).filter(Server.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already registered")

    server = Server(username=body.username, password=hash_password(body.password))
    db.add(server)
    db.commit()
    db.refresh(server)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    server = db.query(Server).filter(Server.username == body.username).first()
    if server is None or not verify_password(body.password, server.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return TokenResponse(access_token=create_stream_token(str(server.id)))
