from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Callable, Optional

import requests
import websocket

from config import (
    CHECKIN_ENDPOINT,
    BACKEND_PASSWORD,
    CHECKIN_TIMEOUT_S,
    CHECKIN_RETRY_MAX,
    CHECKIN_RETRY_DELAY,
    BACKEND_WS_URL,
    RECONNECT_DELAY,
    QUEUE_MAXSIZE,
)
from model import GroomingDetector
from utils import clean_text, utc_now_iso, log_section

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("grooming.pipeline")


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
            server_info = resp.json()
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


class WSClientThread(threading.Thread):
    """
    Connects to the backend WebSocket and pushes received payloads onto
    `inference_queue`.

    Expected server payload (JSON):
        Batch job from TellMom backend:
        {"content": "*"}

    The thread auto-reconnects on disconnect unless stop() has been called.
    """

    def __init__(
        self,
        url: str,
        token: str,
        inference_queue: queue.Queue,
    ):
        super().__init__(name="WSClientThread", daemon=True)
        self.url = url
        self.token = token
        self.inference_queue = inference_queue
        self._stop_event = threading.Event()
        self._ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

    def send_json(self, payload: dict) -> None:
        if self._ws:
            try:
                self._ws.send(json.dumps(payload))
            except Exception as exc:
                logger.error(f"[ws] Failed to send JSON payload: {exc}")

    def stop(self):
        self._stop_event.set()
        if self._ws:
            self._ws.close()

    def _on_open(self, _):
        logger.info("[ws] Connection established.")
        self.send_json({"type": "auth", "token": self.token})

    def _on_message(self, _, raw: str):
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise exc

        # Attempt to insert task into queue
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
        self.result_callback = result_callback
        self.response_sender = response_sender
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("[inference] InferenceThread ready.")
        while not self._stop_event.is_set():
            try:
                item = self.inference_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                # Bypass the input if there's nothing inside
                raw_text = item.get("content", "").strip()
                request_id = item.get("request_id")
                if len(raw_text) == 0:
                    continue

                cleaned_text = clean_text(raw_text)
                logger.info(f"Input text: {raw_text}")
                result = self.detector.predict(text=cleaned_text)

                if self.result_callback:
                    self.result_callback(
                        {"has_pedo": bool(result[0]), "probability": result[1]}
                    )

                if self.response_sender:
                    response_payload = {
                        "request_id": request_id,
                        "result": {
                            "has_pedo": bool(result[0]),
                            "probability": result[1],
                        },
                    }
                    self.response_sender(response_payload)

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

        self._queue = queue.Queue(maxsize=self._queue_maxsize)

        self._detector: Optional[GroomingDetector] = None
        self._inf_thread: Optional[InferenceThread] = None

    def start(self, block: bool = True) -> None:
        """
        Perform check-in, load model, and start both threads.

        Args:
            block: If True (default), keep the main thread alive until
                   KeyboardInterrupt.  Set False if you want non-blocking
                   control (e.g. in tests or when embedded in a larger app).
        """
        log_section(logger, "Server check-in")
        # Checkin with the server backend
        server_info = server_checkin(
            endpoint=self._checkin_endpoint,
            password=self._password,
        )
        logger.info(f"Server acknowledged: {server_info}")

        token = server_info["token"]
        self._ws_thread = WSClientThread(self._ws_url, token, self._queue)

        # Load detector
        log_section(logger, "Loading grooming detector")
        self._detector = GroomingDetector()

        # Start pipeline threads
        log_section(logger, "Starting pipeline threads")
        self._inf_thread = InferenceThread(
            self._detector,
            self._queue,
            self._result_callback,
            response_sender=self._ws_thread.send_json,
        )

        self._inf_thread.start()
        self._ws_thread.start()
        logger.info("Pipeline running. Press Ctrl-C to stop.")

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


if __name__ == "__main__":
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device}")

    pipeline = InferencePipeline(
        ws_url=BACKEND_WS_URL,
        password=BACKEND_PASSWORD,
        checkin_endpoint=CHECKIN_ENDPOINT,
    )
    pipeline.start(block=True)
