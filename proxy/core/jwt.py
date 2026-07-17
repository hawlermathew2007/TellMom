import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from proxy.core import config

ALGORITHM = config.JWT_ALGORITHM


# TODO: do sth about the configuration linter complain later
def create_stream_token(server_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "scope": "server:stream",
        "sub": server_id,
        "iat": now,
        "exp": now + timedelta(hours=config.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def decode_stream_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if payload.get("scope") != "server:stream":
        raise HTTPException(status_code=401, detail="Invalid token scope")
    return payload
