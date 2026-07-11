from pathlib import Path

import joblib
from sentence_transformers import SentenceTransformer
from config import (
    CHECKPOINT_DIR,
    CLASSIFIER_PATH,
    MODEL_NAME,
    DEVICE,
    SCALER_PATH,
)
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class GroomingDetector:
    def __init__(
        self,
        model_name=MODEL_NAME,
        checkpoint_dir=CHECKPOINT_DIR,
        device=DEVICE,
    ):
        logger.info(f"Loading SimCSE encoder: {model_name}  device={device}")
        self.encoder = SentenceTransformer(model_name, device=device)

        scaler_path = checkpoint_dir / SCALER_PATH
        classifier_path = checkpoint_dir / CLASSIFIER_PATH
        logger.info(f"Loading scaler from: {scaler_path}")
        logger.info(f"Loading classifier from: {classifier_path}")
        self._load_models(scaler_path, classifier_path)

    def _load_models(self, classifier_path: Path, scaler_path: Path):
        if not classifier_path.exists():
            raise FileNotFoundError(
                f"Classifier checkpoint not found: {classifier_path}\nRun the training pipeline first."
            )

        if not scaler_path.exists():
            raise FileNotFoundError(
                f"Classifier checkpoint not found: {scaler_path}\nRun the training pipeline first."
            )

        self.scaler = joblib.load(scaler_path)
        self.clf = joblib.load(classifier_path)

    # TODO: expand this to do batch inference later
    def predict(self, text: str) -> Tuple[int, float]:
        # NOTE: encoder accepts a list of string, allowing for batching
        emb = self.encoder.encode(
            [text], convert_to_numpy=True, normalize_embeddings=False
        )
        emb_s = self.scaler.transform(emb)

        # NOTE: the 0 index is to get the first inference result only (no batching)
        # NOTE: The 1 index is to get the predatory id probability only
        label = int(self.clf.predict(emb_s)[0])
        prob = float(self.clf.predict_proba(emb_s)[0][1])
        return label, prob
