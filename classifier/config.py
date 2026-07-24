import os
import torch
import pathlib
from pathlib import Path
from dotenv import load_dotenv

BASE = pathlib.Path(__file__).parent.resolve()
load_dotenv(BASE / ".env")

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/classifier/stream")
BACKEND_PASSWORD = os.getenv("BACKEND_PASSWORD", "1234")

CHECKIN_ENDPOINT = f"{BACKEND_BASE_URL}/classifier/checkin"
CHECKIN_TIMEOUT_S = 10
CHECKIN_RETRY_MAX = 3
CHECKIN_RETRY_DELAY = 5

CHECKPOINT_DIR = Path("checkpoints")
SCALER_PATH = "scaler_simcse_base_roberta.joblib"
CLASSIFIER_PATH = "svm_simcse_base_roberta.joblib"
MODEL_NAME = "princeton-nlp/sup-simcse-roberta-base"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

QUEUE_MAXSIZE = 512
RECONNECT_DELAY = 5
