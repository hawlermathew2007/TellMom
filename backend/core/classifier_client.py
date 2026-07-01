import asyncio
import json

from core import config
from schemas.classifier import ClassifierResult


class ClassifierClient:
    def __init__(self):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self.connected: bool = False
        self._queue_lock = asyncio.Lock()

    async def connect(self) -> None:
        try:
            self._reader, self._writer = await asyncio.open_connection(
                config.COLAB_TCP_HOST,
                config.COLAB_TCP_PORT,
            )
            self.connected = True
        except (OSError, ConnectionError) as exc:
            self.connected = False
            raise ConnectionError(
                f"Failed to connect to classifier at "
                f"{config.COLAB_TCP_HOST}:{config.COLAB_TCP_PORT}"
            ) from exc

    async def classify(self, raw: str) -> ClassifierResult:
        async with self._queue_lock:
            return await self._classify_unlocked(raw)

    async def _classify_unlocked(self, raw: str) -> ClassifierResult:
        if not self.connected or self._reader is None or self._writer is None:
            raise RuntimeError("Classifier not connected")

        try:
            payload = json.dumps({"content": raw}) + "\n"
            self._writer.write(payload.encode())
            await self._writer.drain()

            response_line = await self._reader.readline()
            if not response_line:
                self.connected = False
                raise ConnectionError("Classifier connection closed")

            result = json.loads(response_line.decode())
            return ClassifierResult.model_validate(result)

        except (OSError, ConnectionError, asyncio.IncompleteReadError) as exc:
            self.connected = False
            raise exc

    async def ensure_connected(self) -> None:
        if not self.connected:
            await self.connect()


classifier_client = ClassifierClient()
