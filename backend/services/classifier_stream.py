import asyncio
import json
import logging
import uuid

from fastapi import WebSocket

from schemas.ingest import ClassifierResultItem, ClassifyRequest, ClassifyResponse
from schemas.classifier import ClassifierResult

logger = logging.getLogger(__name__)


class ClassifierStreamManager:
    def __init__(self) -> None:
        self._websocket: WebSocket | None = None
        self._pending: dict[str, asyncio.Future[list[ClassifierResultItem]]] = {}

    @property
    def connected(self) -> bool:
        return self._websocket is not None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
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
            future.set_result(response.results)

    async def classify(
        self,
        platform: str,
        server_id: str,
        chat_group: dict[str, list[str]],
        *,
        timeout: float = 60.0,
    ) -> list[ClassifierResult]:
        if self._websocket is None:
            raise ConnectionError("Classifier not connected on /learner_stream")

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[list[ClassifierResultItem]] = loop.create_future()
        self._pending[request_id] = future

        job = ClassifyRequest(
            request_id=request_id,
            platform=platform,
            server_id=server_id,
            chat_group=chat_group,
        )
        try:
            await self._websocket.send_json(job.model_dump())
            results = await asyncio.wait_for(future, timeout=timeout)
            return [
                ClassifierResult(user_id=item.user_id, is_pedo=item.is_pedo)
                for item in results
            ]
        except Exception:
            self._pending.pop(request_id, None)
            raise


classifier_stream = ClassifierStreamManager()
