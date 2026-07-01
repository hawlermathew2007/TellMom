import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from core import config

ALGORITHM = config.JWT_ALGORITHM


def create_stream_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "scope": "classifier:stream",
        "created_time": now,
        "expiry_time": now + timedelta(hours=config.CLASSIFIER_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, config.CLASSIFIER_JWT_SECRET, algorithm=ALGORITHM)


def decode_stream_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.CLASSIFIER_JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if payload.get("scope") != "classifier:stream":
        raise HTTPException(status_code=401, detail="Invalid token scope")
    return payload
