from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.models import ChildAccount, Parent
from backend.database.session import get_db
from backend.core.dependencies import get_current_parent
from backend.schemas.children import (
    ChildAccountCreate,
    ChildAccountResponse,
    ChildAccountUpdate,
)

router = APIRouter(prefix="/children", tags=["children"])


@router.get("", response_model=list[ChildAccountResponse])
def list_children(
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[ChildAccount]:
    return (
        db.query(ChildAccount)
        .filter(ChildAccount.parent_id == parent.id)
        .order_by(ChildAccount.created_at.desc())
        .all()
    )


@router.post(
    "", response_model=ChildAccountResponse, status_code=status.HTTP_201_CREATED
)
def create_child(
    body: ChildAccountCreate,
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildAccount:
    child = ChildAccount(
        parent_id=parent.id,
        platform=body.platform,
        platform_user_id=body.platform_user_id,
        display_name=body.display_name,
    )
    db.add(child)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This platform account is already registered",
        ) from exc
    db.refresh(child)
    return child


@router.put("/{child_id}", response_model=ChildAccountResponse)
def update_child(
    child_id: int,
    body: ChildAccountUpdate,
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildAccount:
    child = (
        db.query(ChildAccount)
        .filter(ChildAccount.id == child_id, ChildAccount.parent_id == parent.id)
        .first()
    )
    if child is None:
        raise HTTPException(status_code=404, detail="Child account not found")

    if body.platform_user_id is not None:
        child.platform_user_id = body.platform_user_id
    if body.display_name is not None:
        child.display_name = body.display_name

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This platform account is already registered",
        ) from exc
    db.refresh(child)
    return child


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_child(
    child_id: int,
    parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> None:
    child = (
        db.query(ChildAccount)
        .filter(ChildAccount.id == child_id, ChildAccount.parent_id == parent.id)
        .first()
    )
    if child is None:
        raise HTTPException(status_code=404, detail="Child account not found")

    db.delete(child)
    db.commit()
