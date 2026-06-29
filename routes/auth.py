from fastapi import APIRouter, HTTPException, Header, status
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from typing import Optional
import logging
from sqlalchemy.orm import Session
from database import Parent, Consent, Child, get_db
from fastapi import Depends

from config import settings
from models.user import ParentRegister, ParentLogin, ParentConsent, TokenResponse, ParentResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Password hashing
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


@router.post("/register-parent", response_model=TokenResponse)
async def register_parent(
    parent_form: ParentRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new parent account.

    **COPPA Requirement:** Parent must verify email before monitoring starts.
    """
    # Validate passwords match
    if parent_form.password != parent_form.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Check if parent already exists
    existing_parent = db.query(Parent).filter(
        Parent.email == parent_form.email
    ).first()

    if existing_parent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    logger.info(f"[+] Parent registration: {parent_form.email}")

    # Hash password
    hashed_password = hash_password(parent_form.password)

    # Create new parent in DB
    new_parent = Parent(
        email=parent_form.email,
        full_name=parent_form.full_name,
        phone_number=parent_form.phone_number,
        hashed_password=hashed_password,
        email_verified=False  # COPPA: email must be verified
    )

    db.add(new_parent)
    db.commit()
    db.refresh(new_parent)

    logger.info(f"[+] Parent account created: {parent_form.email}")

    # Create JWT token
    token_data = {
        "sub": new_parent.email,
        "type": "parent",
        "email_verified": False,
        "parent_id": new_parent.id,
    }
    access_token = create_access_token(token_data)

    # TODO: Send verification email
    # Email will be send in real production
    logger.info(f"[+] Sending verification email to {parent_form.email}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
        parent=ParentResponse(
            id=new_parent.id,
            email=new_parent.email,
            full_name=new_parent.full_name,
            phone_number=new_parent.phone_number,
            email_verified=new_parent.email_verified,
            consent_signed=False,
            last_login=None,
            created_at=new_parent.created_at
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: ParentLogin, db: Session = Depends(get_db)):
    """
    Parent login with email + password.

    **COPPA Requirement:** Verify parent identity before allowing access to child data.
    """

    parent = db.query(Parent).filter(Parent.email == credentials.email).first()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(credentials.password, parent.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Update last login
    parent.last_login = datetime.utcnow()
    db.commit()

    # Create token
    token_data = {
        "sub": parent.email,
        "type": "parent",
        "email_verified": parent.email_verified,
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_expiration_hours * 3600,
        parent=ParentResponse(
            id=parent.id,
            email=parent.email,
            full_name=parent.full_name,
            phone_number=parent.phone_number,
            email_verified=parent.email_verified,
            consent_signed=True,
            last_login=parent.last_login,
            created_at=parent.created_at
        )
    )


@router.post("/consent")
async def submit_consent(consent: ParentConsent, db: Session = Depends(get_db)):
    """
    Parent grants consent to monitor child's Roblox activity.

    **COPPA Requirement:** Explicit parental consent MUST be obtained before any monitoring.
    Consent notice MUST include:
    - What data is collected (chat messages, timestamps, usernames)
    - How data is used (AI analysis for grooming detection)
    - Parent rights (view, delete, export data)
    - Data retention period
    - Deletion process

    """

    if not consent.consent_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent must grant consent to enable monitoring"
        )

    # TODO: Get parent_id from JWT token (for now use 1)
    parent_id = 1  # Should come from token in production

    try:
        # Create child record
        child = Child(
            parent_id=parent_id,
            name=consent.child_name,
            roblox_username=consent.child_roblox_username,
            roblox_user_id=consent.child_roblox_id
        )
        db.add(child)
        db.commit()
        db.refresh(child)

        # Create consent record
        consent_record = Consent(
            parent_id=parent_id,
            child_id=child.id,
            consent_granted=consent.consent_granted,
            data_retention_days=consent.data_retention_days,
            expires_at=datetime.utcnow() + timedelta(days=consent.data_retention_days),
            notification_method=consent.notification_method,
            high_risk_threshold=consent.high_risk_threshold
        )
        db.add(consent_record)
        db.commit()

        logger.info(f"[+] Consent stored in DB for child: {consent.child_name}")

        # IMPORTANT: Return child_id for redirect
        return {
            "status": "consent_accepted",
            "message": f"Monitoring enabled for {consent.child_name}",
            "child_id": str(child.id),  # ← RETURN THIS
            "child_roblox_id": consent.child_roblox_id
        }

    except Exception as e:
        logger.error(f"[*] Consent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit consent: {str(e)}"
        )


@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """
    Verify parent's email address.

    **COPPA Requirement:** Email must be verified to confirm parent identity.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification token"
        )

    logger.info(f"Email verified: {email}")
    # TODO: Update DB to mark email as verified

    return {"status": "email_verified", "email": email}
