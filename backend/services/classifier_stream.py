import asyncio
import json
import logging
import uuid
from fastapi import WebSocket
from backend.schemas.ingest import ClassifierResultItem, ClassifyResponse

logger = logging.getLogger(__name__)


class ClassifierStreamManager:
    def __init__(self) -> None:
        self._websocket: WebSocket | None = None
        self._pending: dict[str, asyncio.Future[ClassifierResultItem]] = {}
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._websocket is not None

    async def ensure_connected(self, max_retries: int = 5, delay: float = 1.0) -> None:
        """
        Ensure the classifier client is connected. Retries if not.
        """
        for attempt in range(1, max_retries + 1):
            if self.connected:
                return
            logger.info(
                f"Waiting for classifier connection (attempt {attempt}/{max_retries})..."
            )
            await asyncio.sleep(delay)
        if not self.connected:
            raise ConnectionError("Classifier not connected on /stream")

    async def connect(self, websocket: WebSocket) -> None:
        self._websocket = websocket
        logger.info("Classifier connected on /learner_stream")

    def disconnect(self) -> None:
        self._websocket = None
        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionError("Classifier disconnected"))
        self._pending.clear()
        logger.info("Classifier disconnected from /learner_stream")

    def handle_message(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Classifier sent invalid JSON")
            return

        try:
            response = ClassifyResponse.model_validate(payload)
        except Exception:
            logger.warning("Classifier sent unexpected payload: %s", payload)
            return

        future = self._pending.pop(response.request_id, None)
        if future is None:
            logger.warning("No pending request for request_id=%s", response.request_id)
            return
        if not future.done():
            future.set_result(response.result)

    async def classify(
        self,
        raw: str,
        timeout: float = 60.0,
    ) -> ClassifierResultItem:
        if self._websocket is None:
            raise ConnectionError("Classifier not connected on /stream")

        async with self._lock:
            request_id = str(uuid.uuid4())
            loop = asyncio.get_running_loop()
            future: asyncio.Future[ClassifierResultItem] = loop.create_future()
            self._pending[request_id] = future

            job = {"request_id": request_id, "content": raw}
            try:
                await self._websocket.send_json(job)
                result = await asyncio.wait_for(future, timeout=timeout)
                return result

            except Exception:
                self._pending.pop(request_id, None)
                raise

classifier_stream = ClassifierStreamManager()
