import os
from dotenv import load_dotenv

load_dotenv()

CLASSIFIER_PASSWORD = os.getenv("CLASSIFIER_PASSWORD")
assert CLASSIFIER_PASSWORD is not None

CLASSIFIER_JWT_EXPIRE_HOURS = 4

DATABASE_URL = os.getenv("POSTGRES_URL")
assert DATABASE_URL is not None

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
assert GROQ_API_KEY is not None

GROQ_MODEL = "llama-3.3-70b-versatile"

JWT_SECRET = os.getenv("JWT_SECRET")
assert JWT_SECRET is not None

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 60 * 7  # 7 days

CORS_ORIGINS = ["http://localhost:5173"]

MESSAGE_CACHE_TTL_HOURS = 24
CLASSIFIER_MIN_MESSAGES = 7
