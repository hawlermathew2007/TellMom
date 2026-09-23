"""
Public demo endpoint for the website's live playground.

This is not part of the monitoring pipeline: it never talks to a backend, keeps
no database and never logs what it is sent. It wraps the same GroomingDetector
the pipeline uses, so the website scores text with the real model.

    POST /predict   {"messages": ["hey", "how old r u", ...]}
                 -> {"label": 0, "probability": 0.07, "trace": [0.01, 0.03, ...]}
    GET  /health    {"status": "ok"}

`trace` scores every prefix of the conversation, the way the backend scores a
conversation again each time a message arrives (see backend/services/ingest.py),
so the site can show the risk building message by message.

Standard library HTTP on purpose: the classifier project has no web framework,
and this needs two routes.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from model import GroomingDetector
from utils import clean_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("grooming.demo")

HOST = os.getenv("DEMO_HOST", "0.0.0.0")
PORT = int(os.getenv("DEMO_PORT", "8090"))
MAX_MESSAGES = int(os.getenv("DEMO_MAX_MESSAGES", "24"))
MAX_MESSAGE_CHARS = int(os.getenv("DEMO_MAX_MESSAGE_CHARS", "280"))
MAX_BODY_BYTES = 64 * 1024
# Requests per client per minute. Behind Traefik the client is X-Real-IP.
RATE_LIMIT = int(os.getenv("DEMO_RATE_LIMIT", "30"))
CORS_ORIGIN = os.getenv("DEMO_CORS_ORIGIN", "*")

detector: GroomingDetector | None = None
# The SVM and the encoder are not documented as thread safe; one at a time.
predict_lock = threading.Lock()
hits: dict[str, deque[float]] = defaultdict(deque)
hits_lock = threading.Lock()


def rate_limited(client: str) -> bool:
    now = time.monotonic()
    with hits_lock:
        window = hits[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= RATE_LIMIT:
            return True
        window.append(now)
        return False


def score(messages: list[str]) -> dict:
    assert detector is not None
    trace: list[float] = []
    label = 0
    with predict_lock:
        for i in range(1, len(messages) + 1):
            text = clean_text(" ".join(messages[:i]))
            if not text:
                trace.append(0.0)
                continue
            label, prob = detector.predict(text)
            trace.append(round(prob, 4))
    return {"label": label, "probability": trace[-1], "trace": trace}


class Handler(BaseHTTPRequestHandler):
    server_version = "tellmom-demo"

    # Default logging prints the request line only, never the body; keep it
    # quiet anyway so nothing about a visitor ends up in container logs.
    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        if self.path.rstrip("/").endswith("/health"):
            ready = detector is not None
            self._send(200 if ready else 503, {"status": "ok" if ready else "loading"})
            return
        self._send(404, {"detail": "Not found"})

    def do_POST(self) -> None:
        if not self.path.rstrip("/").endswith("/predict"):
            self._send(404, {"detail": "Not found"})
            return
        if detector is None:
            self._send(503, {"detail": "The model is still loading. Try again in a minute."})
            return

        client = self.headers.get("X-Real-IP") or self.client_address[0]
        if rate_limited(client):
            self._send(429, {"detail": "Too many requests. Wait a minute and try again."})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(413, {"detail": "Request body is empty or too large."})
            return

        try:
            payload = json.loads(self.rfile.read(length))
            messages = payload["messages"]
            if not isinstance(messages, list) or not all(isinstance(m, str) for m in messages):
                raise ValueError
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._send(400, {"detail": 'Send {"messages": ["...", "..."]}.'})
            return

        messages = [m.strip()[:MAX_MESSAGE_CHARS] for m in messages if m.strip()]
        messages = messages[-MAX_MESSAGES:]
        if not messages:
            self._send(400, {"detail": "Send at least one message."})
            return

        try:
            self._send(200, score(messages))
        except Exception:
            logger.exception("[demo] prediction failed")
            self._send(500, {"detail": "The classifier failed on this input."})


def main() -> None:
    global detector
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    logger.info(f"[demo] Listening on {HOST}:{PORT}; loading the model …")
    # Bind first so /health answers "loading" while the encoder downloads.
    threading.Thread(target=server.serve_forever, daemon=True).start()
    detector = GroomingDetector()
    logger.info("[demo] Model ready.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
