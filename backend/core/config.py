import os
from dotenv import load_dotenv

load_dotenv()

COLAB_TCP_HOST = os.getenv("COLAB_TCP_HOST", "localhost")
COLAB_TCP_PORT = int(os.getenv("COLAB_TCP_PORT", "9999"))
CLASSIFIER_PASSWORD = os.getenv("CLASSIFIER_PASSWORD", "1234")
CLASSIFIER_JWT_SECRET = os.getenv("CLASSIFIER_JWT_SECRET", "verysecret")
CLASSIFIER_JWT_EXPIRE_HOURS = 4

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tellmom:tellmom@localhost:5432/tellmom",
)

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60 * 60 * 7))  # 7 days

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

MESSAGE_CACHE_TTL_HOURS = int(os.getenv("MESSAGE_CACHE_TTL_HOURS", "24"))
CLASSIFIER_MIN_MESSAGES = int(os.getenv("CLASSIFIER_MIN_MESSAGES", "7"))
