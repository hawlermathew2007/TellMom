import os

from dotenv import load_dotenv

load_dotenv()

COLAB_TCP_HOST = os.getenv("COLAB_TCP_HOST", "localhost")
COLAB_TCP_PORT = int(os.getenv("COLAB_TCP_PORT", "9999"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tellmom:tellmom@localhost:5432/tellmom",
)

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
