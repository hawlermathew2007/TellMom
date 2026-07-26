import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
env_file = BASE_DIR / ".env" if Path(BASE_DIR / ".env").exists() else BASE_DIR / ".env.example"
load_dotenv(env_file)

HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", 8001))
API_URL = os.getenv("API_URL", "http://localhost:8001")

CONFIG_FILE = BASE_DIR / "config.yaml"
