from pathlib import Path

import joblib
from sentence_transformers import SentenceTransformer
from .config import CHECKPOINT_DIR, EMB_KEY, CLF_KEY, MODEL_NAME, DEVICE
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class GroomingDetector:
    def __init__(
        self,
        model_name=MODEL_NAME,
        emb_key=EMB_KEY,
        clf_key=CLF_KEY,
        checkpoint_dir=CHECKPOINT_DIR,
        device=DEVICE,
    ):
        logger.info(f"Loading SimCSE encoder: {model_name}  device={device}")
        self.encoder = SentenceTransformer(model_name, device=device)

        safe_key = emb_key.replace(" ", "_").replace("/", "-")
        clf_path = checkpoint_dir / f"clf_{safe_key}_{clf_key}.joblib"
        logger.info(f"Loading classifier from: {clf_path}")
        self._load_models(clf_path)

    def _load_models(self, clf_path: Path):
        if not clf_path.exists():
            raise FileNotFoundError(
                f"Classifier checkpoint not found: {clf_path}\nRun the training pipeline first."
            )

        bundle = joblib.load(clf_path)
        self.scaler = bundle["scaler"]
        self.clf = bundle["clf"]

    # TODO: expand this to do batch inference later
    def predict(self, text: str) -> Tuple[int, float]:
        # NOTE: encoder accepts a list of string, allowing for batching
        emb = self.encoder.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=False
        )
        emb_s = self.scaler.transform(emb)

        # NOTE: the 0 index is to get the first inference result only (no batching)
        # NOTE: The 1 index is to get the predatory id probability only
        label = int(self.clf.predict(emb_s)[0])
        prob = float(self.clf.predict_proba(emb_s)[0][1])
        return label, prob
