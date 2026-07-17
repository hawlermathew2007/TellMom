import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ServerStreamManager:
    def __init__(self) -> None:
        self._websocket: WebSocket | None = None

    @property
    def connected(self) -> bool:
        return self._websocket is not None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._websocket = websocket

    def disconnect(self) -> None:
        self._websocket = None

    def handle(self, raw: str) -> None:
        pass
