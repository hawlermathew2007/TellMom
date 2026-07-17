from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.models import Parent
from backend.database.session import get_db
from backend.core.dependencies import get_current_parent
from backend.schemas.auth import ParentLogin, ParentRegister, ParentResponse, TokenResponse
from backend.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=ParentResponse, status_code=status.HTTP_201_CREATED
)
def register_parent(body: ParentRegister, db: Session = Depends(get_db)) -> Parent:
    existing = db.query(Parent).filter(Parent.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    parent = Parent(email=body.email, hashed_password=hash_password(body.password))
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


@router.post("/login", response_model=TokenResponse)
def login_parent(body: ParentLogin, db: Session = Depends(get_db)) -> TokenResponse:
    parent = db.query(Parent).filter(Parent.email == body.email).first()
    if parent is None or not verify_password(body.password, parent.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return TokenResponse(access_token=create_access_token(parent.id))


@router.get("/me", response_model=ParentResponse)
def get_me(parent: Parent = Depends(get_current_parent)) -> Parent:
    return parent
