"""
WebSocket Inference Pipeline — Online Grooming Detection
=========================================================
Architecture:
  1. Server check-in (HTTP handshake) — must succeed before anything else
  2. WSClientThread     — receives raw conversation payloads from the backend
  3. InferenceThread    — encodes text, classifies, emits structured results

Output per conversation:
  {
    "conv_id":         str,
    "is_predator":     bool,          # binary flag
    "risk_level":      "normal" | "medium" | "high",
    "probability":     float,         # P(predatory), 0.0 – 1.0
    "message_count":   int,
    "text_preview":    str,
    "flagged_at":      ISO-8601 str
  }

Risk thresholds (configurable in RISK_THRESHOLDS below):
  probability < 0.40  → "normal"
  0.40 ≤ prob < 0.70  → "medium"
  probability ≥ 0.70  → "high"

Dependencies:
  pip install websocket-client sentence-transformers scikit-learn joblib torch requests
"""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

import joblib
import requests
import websocket
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("grooming.pipeline")

# --- Server ---
BACKEND_BASE_URL = "http://localhost:8000"  # REST base
BACKEND_WS_URL = "ws://localhost:8000/learner_stream"
BACKEND_PASSWORD = "1234"
TCP_HOST = "0.0.0.0"
TCP_PORT = 9999

CHECKIN_ENDPOINT = f"{BACKEND_BASE_URL}/checkin"  # GET or POST
CHECKIN_TIMEOUT_S = 10
CHECKIN_RETRY_MAX = 3
CHECKIN_RETRY_DELAY = 5  # seconds between retries

# --- Model ---
CHECKPOINT_DIR = Path("checkpoints")
EMB_KEY = "SimCSE-Base-RoBERTa"
CLF_KEY = "SVM"
MODEL_NAME = "princeton-nlp/sup-simcse-roberta-base"
DEVICE = "cuda"  # set to "cuda" if GPU is available

# --- Queue ---
QUEUE_MAXSIZE = 512
RECONNECT_DELAY = 5

# --- Risk thresholds ---
RISK_THRESHOLDS: Dict[str, float] = {
    "high": 0.70,  # probability >= this → "high"
    "medium": 0.40,  # probability >= this → "medium"
    # below "medium" threshold → "normal"
}


def clean_text(text: str) -> str:
    """Light cleaning matching Section 3.1 of the training pipeline."""
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    tokens = text.split()
    filtered = [
        tok
        for tok in tokens
        if sum(1 for c in tok if ord(c) < 128) / max(len(tok), 1) >= 0.70
    ]
    return " ".join(filtered).strip()


def probability_to_risk(probability: float) -> str:
    """Map a [0, 1] probability to a human-readable risk level."""
    if probability >= RISK_THRESHOLDS["high"]:
        return "high"
    if probability >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "normal"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CheckInError(RuntimeError):
    """Raised when the server check-in fails after all retries."""


def server_checkin(
    endpoint: str = CHECKIN_ENDPOINT,
    password: str = BACKEND_PASSWORD,
    timeout: int = CHECKIN_TIMEOUT_S,
    max_retries: int = CHECKIN_RETRY_MAX,
    retry_delay: int = CHECKIN_RETRY_DELAY,
) -> dict:
    """
    Perform an HTTP check-in handshake with the backend before opening the
    WebSocket connection.

    Sends:
        POST /checkin
        Headers: X-Password: <password>
        Body:    {"client": "grooming-detector", "version": "1.0",
                  "timestamp": "<ISO-8601>"}

    Expects a 2xx response.  The JSON body (if any) is returned.
    Raises CheckInError if every attempt fails.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Password": password,
    }
    body = {
        "client": "grooming-detector",
        "version": "1.0",
        "timestamp": utc_now_iso(),
    }

    last_exc: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        logger.info(f"[check-in] Attempt {attempt}/{max_retries} → POST {endpoint}")
        try:
            resp = requests.post(
                endpoint,
                json=body,
                headers=headers,
                timeout=timeout,
            )
            resp.raise_for_status()

            # Parse optional JSON response; fall back to empty dict
            try:
                server_info = resp.json()
            except ValueError:
                server_info = {}

            logger.info(
                f"[check-in] SUCCESS  HTTP {resp.status_code}  "
                f"server_info={server_info}"
            )
            return server_info

        except requests.HTTPError as exc:
            logger.warning(f"[check-in] HTTP error: {exc}")
            last_exc = exc
        except requests.ConnectionError as exc:
            logger.warning(f"[check-in] Connection refused: {exc}")
            last_exc = exc
        except requests.Timeout as exc:
            logger.warning(f"[check-in] Timed out after {timeout}s: {exc}")
            last_exc = exc

        if attempt < max_retries:
            logger.info(f"[check-in] Retrying in {retry_delay}s …")
            time.sleep(retry_delay)

    raise CheckInError(
        f"Server check-in failed after {max_retries} attempt(s). Last error: {last_exc}"
    )


class GroomingDetector:
    """
    Wraps the SimCSE encoder + trained SVM classifier loaded from disk.

    predict(text) → structured result dict (see module docstring).
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        emb_key: str = EMB_KEY,
        clf_key: str = CLF_KEY,
        checkpoint_dir: Path = CHECKPOINT_DIR,
        device: str = DEVICE,
    ):
        logger.info(f"Loading SimCSE encoder: {model_name}  device={device}")
        self.encoder = SentenceTransformer(model_name, device=device)

        # Build the exact same filename pattern as the training pipeline
        safe_key = emb_key.replace(" ", "_").replace("/", "-")
        clf_path = checkpoint_dir / f"clf_{safe_key}_{clf_key}.joblib"

        if not clf_path.exists():
            raise FileNotFoundError(
                f"Classifier checkpoint not found: {clf_path}\n"
                "Run the training pipeline first (grooming_detection_colab.py)."
            )

        bundle = joblib.load(clf_path)
        self.scaler = bundle["scaler"]
        self.clf = bundle["clf"]
        logger.info(f"Classifier loaded from: {clf_path}")

    def predict(self, text: str, conv_id: str = "—", message_count: int = 0) -> dict:
        """
        Encode one conversation block and return a full prediction dict.

        Args:
            text:          Merged, cleaned conversation text.
            conv_id:       Conversation identifier (for logging / downstream).
            message_count: Original number of messages (metadata only).

        Returns:
            {
              "conv_id":       str,
              "is_predator":   bool,
              "risk_level":    "normal" | "medium" | "high",
              "probability":   float,
              "message_count": int,
              "text_preview":  str,
              "flagged_at":    str   (ISO-8601 UTC, present only when is_predator)
            }
        """
        emb = self.encoder.encode(
            [text], convert_to_numpy=True, normalize_embeddings=False
        )
        emb_s = self.scaler.transform(emb)

        label = int(self.clf.predict(emb_s)[0])
        prob = float(self.clf.predict_proba(emb_s)[0][1])

        risk = probability_to_risk(prob)
        is_pred = label == 1

        result: dict = {
            "conv_id": conv_id,
            "is_predator": is_pred,
            "risk_level": risk,
            "probability": round(prob, 4),
            "message_count": message_count,
            "text_preview": text[:100],
        }

        if is_pred:
            result["flagged_at"] = utc_now_iso()

        return result


class WSClientThread(threading.Thread):
    """
    Connects to the backend WebSocket and pushes received payloads onto
    `inference_queue`.

    Expected server payload (JSON):
        Batch job from TellMom backend:
        {
          "request_id": "uuid",
          "platform":   "roblox",
          "server_id":  "abc123",
          "chat_group": {"user_a": ["hey", "…"], "user_b": ["…"]}
        }

        Legacy single-user payload:
        {
          "conv_id":  "abc123",
          "messages": ["hey", "…"]
        }

    The thread auto-reconnects on disconnect unless stop() has been called.
    """

    def __init__(
        self,
        url: str,
        password: str,
        inference_queue: queue.Queue,
    ):
        super().__init__(name="WSClientThread", daemon=True)
        self.url = f"{url}?token={password}"
        self.inference_queue = inference_queue
        self._stop_event = threading.Event()
        self._ws: Optional[websocket.WebSocketApp] = None

    # ── Public ─────────────────────────────────────────────────────────────

    def send_json(self, payload: dict) -> None:
        if self._ws:
            self._ws.send(json.dumps(payload))

    def stop(self):
        self._stop_event.set()
        if self._ws:
            self._ws.close()

    # ── WebSocket handlers ─────────────────────────────────────────────────

    def _on_open(self, _):
        logger.info("[ws] Connection established.")

    def _on_message(self, _, raw: str):
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            payload = {"text": str(raw)}

        if isinstance(payload.get("chat_group"), dict) and payload.get("request_id"):
            payload["_kind"] = "batch"
            try:
                self.inference_queue.put_nowait(payload)
            except queue.Full:
                logger.warning("[ws] Inference queue full — dropping batch job.")
            return

        # Support both pre-joined text and a list of messages
        if "messages" in payload and isinstance(payload["messages"], list):
            joined = " ".join(str(m) for m in payload["messages"])
            payload["text"] = joined
            payload["message_count"] = len(payload["messages"])
        elif "text" not in payload or not payload["text"].strip():
            logger.debug("[ws] Empty/invalid payload — skipping.")
            return

        payload.setdefault("conv_id", "unknown")
        payload.setdefault("message_count", 0)

        try:
            self.inference_queue.put_nowait(payload)
        except queue.Full:
            logger.warning("[ws] Inference queue full — dropping message.")

    def _on_error(self, _, err):
        logger.error(f"[ws] Error: {err}")

    def _on_close(self, _, code, msg):
        logger.info(f"[ws] Closed (code={code}, msg={msg})")

    def run(self):
        while not self._stop_event.is_set():
            logger.info(f"[ws] Connecting → {self.url}")
            self._ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            self._ws.run_forever()

            if not self._stop_event.is_set():
                logger.info(f"[ws] Reconnecting in {RECONNECT_DELAY}s …")
                time.sleep(RECONNECT_DELAY)

        logger.info("[ws] WSClientThread stopped.")


class InferenceThread(threading.Thread):
    """
    Pulls items from `inference_queue`, runs GroomingDetector, and calls
    `result_callback(result_dict)`.

    The default callback logs the result and returns it; replace with your
    own handler (DB write, REST push, alert webhook, etc.).
    """

    def __init__(
        self,
        detector: GroomingDetector,
        inference_queue: queue.Queue,
        result_callback: Optional[Callable[[dict], None]] = None,
        response_sender: Optional[Callable[[dict], None]] = None,
    ):
        super().__init__(name="InferenceThread", daemon=True)
        self.detector = detector
        self.inference_queue = inference_queue
        self.result_callback = result_callback or self._default_callback
        self.response_sender = response_sender
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    # ── Default result handler ─────────────────────────────────────────────

    @staticmethod
    def _default_callback(result: dict) -> None:
        risk_icons = {"normal": "✅", "medium": "⚠️ ", "high": "🚨"}
        icon = risk_icons.get(result["risk_level"], "?")
        pred_flag = "PREDATOR DETECTED" if result["is_predator"] else "safe"

        logger.info(
            f"{icon} [{pred_flag}]  "
            f"risk={result['risk_level'].upper():<6}  "
            f"p={result['probability']:.4f}  "
            f"conv={result['conv_id']}  "
            f"msgs={result['message_count']}  "
            f"preview='{result['text_preview'][:60]}…'"
        )
        if result["is_predator"]:
            logger.warning(f"  ↳ flagged_at={result.get('flagged_at', 'n/a')}")

    # ── Thread entry ───────────────────────────────────────────────────────

    def run(self):
        logger.info("[inference] InferenceThread ready.")
        while not self._stop_event.is_set():
            try:
                item = self.inference_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if item.get("_kind") == "batch":
                    chat_group = item.get("chat_group", {})
                    results = classify_chat_group(self.detector, chat_group)
                    if self.response_sender is not None:
                        self.response_sender(
                            {
                                "request_id": item["request_id"],
                                "results": results,
                            }
                        )
                    continue

                raw_text = item.get("text", "")
                cleaned_text = clean_text(raw_text)
                conv_id = item.get("conv_id", "unknown")
                msg_count = item.get("message_count", 0)

                result = self.detector.predict(
                    text=cleaned_text,
                    conv_id=conv_id,
                    message_count=msg_count,
                )

                self.result_callback(result)

            except Exception as exc:
                logger.exception(f"[inference] Unhandled error: {exc}")
            finally:
                self.inference_queue.task_done()

        logger.info("[inference] InferenceThread stopped.")


class InferencePipeline:
    """
    Ties check-in + both threads together.

    Flow:
      1. server_checkin()          — HTTP handshake (raises CheckInError on failure)
      2. GroomingDetector()        — load encoder + classifier
      3. WSClientThread.start()    — open WebSocket
      4. InferenceThread.start()   — begin consuming queue

    Example
    -------
    >>> def on_result(result: dict):
    ...     if result["is_predator"]:
    ...         alert_moderation_team(result)
    ...     store_result(result)
    >>>
    >>> pipeline = InferencePipeline(result_callback=on_result)
    >>> pipeline.start()          # blocks until Ctrl-C
    """

    def __init__(
        self,
        ws_url: str = BACKEND_WS_URL,
        password: str = BACKEND_PASSWORD,
        result_callback: Optional[Callable] = None,
        queue_maxsize: int = QUEUE_MAXSIZE,
        checkin_endpoint: str = CHECKIN_ENDPOINT,
    ):
        self._ws_url = ws_url
        self._password = password
        self._result_callback = result_callback
        self._queue_maxsize = queue_maxsize
        self._checkin_endpoint = checkin_endpoint

        self._queue: Optional[queue.Queue] = None
        self._detector: Optional[GroomingDetector] = None
        self._ws_thread: Optional[WSClientThread] = None
        self._inf_thread: Optional[InferenceThread] = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self, block: bool = True) -> None:
        """
        Perform check-in, load model, and start both threads.

        Args:
            block: If True (default), keep the main thread alive until
                   KeyboardInterrupt.  Set False if you want non-blocking
                   control (e.g. in tests or when embedded in a larger app).
        """
        # ── 1. Server check-in ────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("  STEP 1 — Server check-in")
        logger.info("=" * 60)
        server_info = server_checkin(
            endpoint=self._checkin_endpoint,
            password=self._password,
        )
        logger.info(f"Server acknowledged: {server_info}")

        # ── 2. Load detector ──────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("  STEP 2 — Loading grooming detector")
        logger.info("=" * 60)
        self._detector = GroomingDetector()

        # ── 3. Spin up threads ────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info("  STEP 3 — Starting pipeline threads")
        logger.info("=" * 60)
        self._queue = queue.Queue(maxsize=self._queue_maxsize)
        self._ws_thread = WSClientThread(self._ws_url, self._password, self._queue)
        self._inf_thread = InferenceThread(
            self._detector,
            self._queue,
            self._result_callback,
            response_sender=self._ws_thread.send_json,
        )

        self._inf_thread.start()
        self._ws_thread.start()
        logger.info("Pipeline running.  Press Ctrl-C to stop.")

        if block:
            try:
                while self.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nKeyboardInterrupt received — shutting down.")
            finally:
                self.stop()

    def stop(self) -> None:
        if self._ws_thread:
            self._ws_thread.stop()
        if self._inf_thread:
            self._inf_thread.stop()
        if self._ws_thread:
            self._ws_thread.join(timeout=5)
        if self._inf_thread:
            self._inf_thread.join(timeout=5)
        logger.info("Pipeline stopped.")

    def is_alive(self) -> bool:
        return (
            self._ws_thread is not None
            and self._ws_thread.is_alive()
            and self._inf_thread is not None
            and self._inf_thread.is_alive()
        )


def classify_chat_group(
    detector: GroomingDetector,
    chat_group: dict[str, list[str]],
) -> list[dict]:
    """
    Classify each user's messages independently.

    Expected input (from backend ingest):
        {"user_id_a": ["msg1", "msg2"], "user_id_b": ["msg3"]}

    Returns one result per user, aligned with backend ClassifierResult:
        [{"user_id": str, "is_pedo": bool}, ...]
    """
    results: list[dict] = []
    for user_id, messages in chat_group.items():
        if not messages:
            results.append({"user_id": user_id, "is_pedo": False})
            continue

        raw = " ".join(str(message) for message in messages)
        cleaned = clean_text(raw)
        prediction = detector.predict(
            text=cleaned,
            conv_id=user_id,
            message_count=len(messages),
        )
        results.append(
            {
                "user_id": user_id,
                "is_pedo": prediction["is_predator"],
            }
        )
    return results


class TCPServerThread(threading.Thread):
    """
    Listens for newline-delimited JSON requests from the TellMom backend.

    Request:
        {
          "platform":  "roblox",
          "server_id": "abc123",
          "chat_group": {
            "user_a": ["hey", "how old are you?"],
            "user_b": ["im 12"]
          }
        }

    Response:
        [
          {"user_id": "user_a", "is_pedo": true},
          {"user_id": "user_b", "is_pedo": false}
        ]
    """

    def __init__(
        self,
        host: str,
        port: int,
        detector: GroomingDetector,
    ):
        super().__init__(name="TCPServerThread", daemon=True)
        self.host = host
        self.port = port
        self.detector = detector
        self._stop_event = threading.Event()
        self._server_socket: Optional[socket.socket] = None

    def stop(self):
        self._stop_event.set()
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass

    def _handle_client(self, conn: socket.socket) -> None:
        with conn:
            buffer = b""
            while b"\n" not in buffer:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buffer += chunk

            request_line = buffer.split(b"\n", 1)[0]
            try:
                payload = json.loads(request_line.decode())
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning(f"[tcp] Invalid request payload: {exc}")
                conn.sendall(b"[]\n")
                return

            chat_group = payload.get("chat_group", {})
            if not isinstance(chat_group, dict):
                logger.warning("[tcp] chat_group must be a dict — skipping.")
                conn.sendall(b"[]\n")
                return

            normalized_group: dict[str, list[str]] = {}
            for user_id, messages in chat_group.items():
                if isinstance(messages, list):
                    normalized_group[str(user_id)] = [str(message) for message in messages]

            results = classify_chat_group(self.detector, normalized_group)
            conn.sendall((json.dumps(results) + "\n").encode())

    def run(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen()
        logger.info(f"[tcp] Listening on {self.host}:{self.port}")

        while not self._stop_event.is_set():
            try:
                self._server_socket.settimeout(1.0)
                conn, addr = self._server_socket.accept()
            except TimeoutError:
                continue
            except OSError:
                if not self._stop_event.is_set():
                    logger.exception("[tcp] Accept failed.")
                break

            logger.info(f"[tcp] Connection from {addr}")
            threading.Thread(
                target=self._handle_client,
                args=(conn,),
                daemon=True,
            ).start()

        logger.info("[tcp] TCPServerThread stopped.")


class ClassifierTCPServer:
    """Load the detector and serve per-user classifications over TCP."""

    def __init__(
        self,
        host: str = TCP_HOST,
        port: int = TCP_PORT,
    ):
        self._host = host
        self._port = port
        self._detector: Optional[GroomingDetector] = None
        self._tcp_thread: Optional[TCPServerThread] = None

    def start(self, block: bool = True) -> None:
        logger.info("=" * 60)
        logger.info("  Loading grooming detector")
        logger.info("=" * 60)
        self._detector = GroomingDetector()

        logger.info("=" * 60)
        logger.info("  Starting TCP classifier server")
        logger.info("=" * 60)
        self._tcp_thread = TCPServerThread(self._host, self._port, self._detector)
        self._tcp_thread.start()
        logger.info("Classifier TCP server running. Press Ctrl-C to stop.")

        if block:
            try:
                while self.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nKeyboardInterrupt received — shutting down.")
            finally:
                self.stop()

    def stop(self) -> None:
        if self._tcp_thread:
            self._tcp_thread.stop()
            self._tcp_thread.join(timeout=5)
        logger.info("Classifier TCP server stopped.")

    def is_alive(self) -> bool:
        return self._tcp_thread is not None and self._tcp_thread.is_alive()
def classify_conversations(
    conversations: list[list[str]],
    conv_ids: Optional[list[str]] = None,
) -> list[dict]:
    """
    Batch-classify a list of conversations without spinning up a WebSocket.

    Args:
        conversations: List of conversations, each a list of message strings.
        conv_ids:      Optional list of IDs aligned with `conversations`.

    Returns:
        List of result dicts (one per conversation).
    """
    detector = GroomingDetector()
    ids = conv_ids or [f"conv_{i}" for i in range(len(conversations))]

    results = []
    for cid, messages in zip(ids, conversations):
        raw = " ".join(messages)
        cleaned = clean_text(raw)
        result = detector.predict(
            text=cleaned,
            conv_id=cid,
            message_count=len(messages),
        )
        results.append(result)

    return results


if __name__ == "__main__":
    import torch

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {DEVICE}")

    pipeline = InferencePipeline(
        ws_url=BACKEND_WS_URL,
        password=BACKEND_PASSWORD,
        checkin_endpoint=CHECKIN_ENDPOINT,
    )
    pipeline.start(block=True)
