import os
import pathlib
from dotenv import load_dotenv

BASE = pathlib.Path(__file__).parent.parent.resolve()
ENV_FILE = (
    BASE / ".env" if pathlib.Path(BASE / ".env").exists() else BASE / ".env.example"
)
load_dotenv(ENV_FILE)

HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", 8080))

DATABASE_URL = os.getenv("POSTGRES_URL")
assert DATABASE_URL is not None

JWT_ALGORITHM = "HS256"
assert JWT_ALGORITHM is not None

JWT_SECRET = os.getenv("JWT_SECRET")
assert JWT_SECRET is not None

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 24))

CORS_ORIGINS = ["http://localhost:5173"]
