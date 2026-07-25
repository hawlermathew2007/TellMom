import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from backend.core import config

ALGORITHM = config.JWT_ALGORITHM


# TODO: this way of doing it is kind of dumb, now theres a mismatch wit proxy server stream
def create_stream_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "scope": "classifier:stream",
        "iat": now,
        "exp": now + timedelta(hours=config.CLASSIFIER_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def decode_stream_token(token: str, scope: bool = True) -> dict:
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if scope and payload.get("scope") != "classifier:stream":
        raise HTTPException(status_code=401, detail="Invalid token scope")

    return payload
