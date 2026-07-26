import os
import pathlib
from dotenv import load_dotenv

BASE = pathlib.Path(__file__).parent.parent.resolve()
load_dotenv(BASE / ".env")
load_dotenv()

DATABASE_URL = os.getenv("POSTGRES_URL")
assert DATABASE_URL is not None

JWT_ALGORITHM = "HS256"
assert JWT_ALGORITHM is not None

JWT_SECRET = os.getenv("JWT_SECRET")
assert JWT_SECRET is not None

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 24))

CORS_ORIGINS = ["http://localhost:5173"]
