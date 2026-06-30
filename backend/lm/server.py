import json
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import joblib
import numpy as np
import websocket  # websocket-client
from sentence_transformers import SentenceTransformer

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("ws_inference")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  — edit these to match your setup
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_WS_URL   = "ws://localhost:5000/learner_stream"   # or wss://…
BACKEND_PASSWORD = "1234"

# Paths to the checkpoint artefacts produced by grooming_detection_colab.py
CHECKPOINT_DIR  = Path("checkpoints")
EMB_KEY         = "SimCSE-Base-RoBERTa"
CLF_KEY         = "SVM"
MODEL_NAME      = "princeton-nlp/sup-simcse-roberta-base"

INFERENCE_DEVICE = "cpu"     # "cuda" if GPU is available
RECONNECT_DELAY  = 5         # seconds between WebSocket reconnect attempts
QUEUE_MAXSIZE    = 256


# ─────────────────────────────────────────────────────────────────────────────
# MODEL LOADER
# ─────────────────────────────────────────────────────────────────────────────

class GroomingDetector:
    """
    Wraps the SimCSE encoder + trained SVM classifier.
    Loads the classifier from the checkpoint saved by the training pipeline.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        emb_key: str    = EMB_KEY,
        clf_key: str    = CLF_KEY,
        checkpoint_dir: Path = CHECKPOINT_DIR,
        device: str     = INFERENCE_DEVICE,
    ):
        logger.info("Loading SimCSE encoder …")
        self.encoder = SentenceTransformer(model_name, device=device)

        clf_path = checkpoint_dir / f"clf_{emb_key.replace(' ','_').replace('/','_')}_{clf_key}.joblib"
        if not clf_path.exists():
            raise FileNotFoundError(
                f"Classifier checkpoint not found: {clf_path}\n"
                "Run the training pipeline first (grooming_detection_colab.py)."
            )
        bundle = joblib.load(clf_path)
        self.scaler = bundle["scaler"]
        self.clf    = bundle["clf"]
        logger.info(f"Classifier loaded from {clf_path}")

    def predict(self, text: str) -> dict:
        """
        Encode one conversation text and return a prediction dict:
            {
              "label":       0 | 1,           # 1 = predatory
              "probability": float,            # P(predatory)
              "text_preview": str              # first 80 chars
            }
        """
        emb   = self.encoder.encode([text], convert_to_numpy=True)
        emb_s = self.scaler.transform(emb)
        label = int(self.clf.predict(emb_s)[0])
        prob  = float(self.clf.predict_proba(emb_s)[0][1])
        return {
            "label":        label,
            "probability":  round(prob, 4),
            "text_preview": text[:80],
        }


# ─────────────────────────────────────────────────────────────────────────────
# THREAD 1 — WebSocket client
# ─────────────────────────────────────────────────────────────────────────────

class WSClientThread(threading.Thread):
    """
    Connects to the backend WebSocket and forwards received messages
    onto `inference_queue`.

    The server is expected to push JSON objects with at least a "text" key:
        {"text": "hey can we keep this just between us …", "conv_id": "abc123"}

    If the connection drops, this thread retries automatically every
    RECONNECT_DELAY seconds until `stop()` is called.
    """

    def __init__(
        self,
        url: str,
        password: str,
        inference_queue: queue.Queue,
    ):
        super().__init__(name="WSClientThread", daemon=True)
        self.url             = f"{url}?token={password}"
        self.inference_queue = inference_queue
        self._stop_event     = threading.Event()
        self._ws: Optional[websocket.WebSocketApp] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def stop(self):
        self._stop_event.set()
        if self._ws:
            self._ws.close()

    # ── Internal handlers ─────────────────────────────────────────────────────

    def _on_open(self, ws):
        logger.info("WebSocket connected.")

    def _on_message(self, ws, raw_message):
        try:
            payload = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            # Treat raw string as plain conversation text
            payload = {"text": str(raw_message)}

        text = payload.get("text", "").strip()
        if not text:
            logger.debug("Received empty payload — skipping.")
            return

        # Attach any extra metadata the server sent
        item = {**payload, "text": text}

        try:
            self.inference_queue.put_nowait(item)
        except queue.Full:
            logger.warning("Inference queue full — dropping message.")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, code, msg):
        logger.info(f"WebSocket closed ({code}: {msg})")

    # ── Thread entry ──────────────────────────────────────────────────────────

    def run(self):
        while not self._stop_event.is_set():
            logger.info(f"Connecting to {self.url} …")
            self._ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self._ws.run_forever()

            if not self._stop_event.is_set():
                logger.info(f"Reconnecting in {RECONNECT_DELAY}s …")
                time.sleep(RECONNECT_DELAY)

        logger.info("WSClientThread stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# THREAD 2 — Inference worker
# ─────────────────────────────────────────────────────────────────────────────

class InferenceThread(threading.Thread):
    """
    Pulls items from `inference_queue`, runs them through GroomingDetector,
    and calls `result_callback(item, prediction)`.

    The default callback just logs the result; replace it with your own
    handler (e.g. push to a database, send an alert, return over WebSocket).
    """

    def __init__(
        self,
        detector: GroomingDetector,
        inference_queue: queue.Queue,
        result_callback: Optional[Callable] = None,
    ):
        super().__init__(name="InferenceThread", daemon=True)
        self.detector        = detector
        self.inference_queue = inference_queue
        self.result_callback = result_callback or self._default_callback
        self._stop_event     = threading.Event()

    def stop(self):
        self._stop_event.set()

    @staticmethod
    def _default_callback(item: dict, prediction: dict):
        flag  = "[*] PREDATORY" if prediction["label"] == 1 else "[+] safe"
        prob  = prediction["probability"]
        conv  = item.get("conv_id", "—")
        preview = prediction["text_preview"]
        logger.info(f"[{flag}]  p={prob:.3f}  conv={conv}  text='{preview}…'")

    def run(self):
        logger.info("InferenceThread ready.")
        while not self._stop_event.is_set():
            try:
                item = self.inference_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                prediction = self.detector.predict(item["text"])
                self.result_callback(item, prediction)
            except Exception as exc:
                logger.exception(f"Inference error: {exc}")
            finally:
                self.inference_queue.task_done()

        logger.info("InferenceThread stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# MANAGER — ties both threads together
# ─────────────────────────────────────────────────────────────────────────────

class InferencePipeline:
    """
    Convenience wrapper that starts and stops both threads together.

    Example
    -------
    >>> def my_callback(item, pred):
    ...     if pred["label"] == 1:
    ...         alert_moderation_team(item["conv_id"])
    >>>
    >>> pipeline = InferencePipeline(result_callback=my_callback)
    >>> pipeline.start()
    >>> # … runs until Ctrl-C or pipeline.stop()
    """

    def __init__(
        self,
        ws_url: str         = BACKEND_WS_URL,
        password: str       = BACKEND_PASSWORD,
        result_callback     = None,
        queue_maxsize: int  = QUEUE_MAXSIZE,
    ):
        self._queue = queue.Queue(maxsize=queue_maxsize)

        logger.info("Initialising grooming detector …")
        self._detector = GroomingDetector()

        self._ws_thread  = WSClientThread(ws_url, password, self._queue)
        self._inf_thread = InferenceThread(
            self._detector, self._queue, result_callback
        )

    def start(self):
        logger.info("Starting pipeline …")
        self._inf_thread.start()
        self._ws_thread.start()

    def stop(self):
        logger.info("Stopping pipeline …")
        self._ws_thread.stop()
        self._inf_thread.stop()
        self._ws_thread.join(timeout=5)
        self._inf_thread.join(timeout=5)
        logger.info("Pipeline stopped.")

    def is_alive(self) -> bool:
        return self._ws_thread.is_alive() and self._inf_thread.is_alive()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Optional: define a custom result handler
    def on_result(item: dict, prediction: dict):
        """Replace this with your own downstream logic."""
        flag = "PREDATORY" if prediction["label"] == 1 else "safe"
        print(
            f"[{flag}] p={prediction['probability']:.3f} "
            f"| conv={item.get('conv_id', '?')} "
            f"| {prediction['text_preview']!r}"
        )

    pipeline = InferencePipeline(
        ws_url=BACKEND_WS_URL,
        password=BACKEND_PASSWORD,
        result_callback=on_result,
    )

    pipeline.start()

    try:
        while pipeline.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down …")
    finally:
        pipeline.stop()
