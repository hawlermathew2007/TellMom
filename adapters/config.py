import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
env_file = (
    BASE_DIR / ".env" if Path(BASE_DIR / ".env").exists() else BASE_DIR / ".env.example"
)
load_dotenv(env_file)

HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", 8001))
PROXY_URL = os.getenv("PROXY_URL", "http://localhost:8080")
API_URL = f"http://{HOST}:{PORT}/api"

CONFIG_FILE = BASE_DIR / "config.yaml"
RECONNECT_INTERVAL = 5
