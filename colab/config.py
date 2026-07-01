import os
from pathlib import Path

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/learner_stream")
BACKEND_PASSWORD = os.getenv("BACKEND_PASSWORD", "1234")
TCP_HOST = "0.0.0.0"
TCP_PORT = 9999

CHECKIN_ENDPOINT = f"{BACKEND_BASE_URL}/checkin"
CHECKIN_TIMEOUT_S = 10
CHECKIN_RETRY_MAX = 3
CHECKIN_RETRY_DELAY = 5

CHECKPOINT_DIR = Path("checkpoints")
SCALER_PATH = "scaler_simcse_base_roberta.joblib"
CLASSIFIER_PATH = "svm_simcse_base_roberta.joblib"
MODEL_NAME = "princeton-nlp/sup-simcse-roberta-base"
DEVICE = "cuda"

QUEUE_MAXSIZE = 512
RECONNECT_DELAY = 5

RISK_THRESHOLDS = {
    "high": 0.70,
    "medium": 0.40,
}
