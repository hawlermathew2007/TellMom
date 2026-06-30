from fastapi import WebSocket


class AlertConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, parent_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(parent_id, []).append(websocket)

    def disconnect(self, parent_id: int, websocket: WebSocket) -> None:
        conns = self._connections.get(parent_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(parent_id, None)

    async def notify_parent(self, parent_id: int, payload: dict) -> None:
        for ws in list(self._connections.get(parent_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(parent_id, ws)

    async def notify_parents(self, parent_ids: set[int], payload: dict) -> None:
        for parent_id in parent_ids:
            await self.notify_parent(parent_id, payload)


alert_manager = AlertConnectionManager()
