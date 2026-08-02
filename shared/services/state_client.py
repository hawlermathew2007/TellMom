from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Awaitable, Callable

import websockets

from shared.schemas.stream import Command, StreamMessageType

logger = logging.getLogger(__name__)

SnapshotCallback = Callable[[dict[str, Any]], Any | Awaitable[Any]]
StatusCallback = Callable[[bool, str], Any | Awaitable[Any]]


class CommandError(RuntimeError):
    """The server accepted the command but it did not succeed."""


def websocket_url(base_url: str, path: str) -> str:
    scheme_swapped = base_url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{scheme_swapped.rstrip('/')}{path}"


class StateStreamClient:
    """Client side of a state stream.

    Keeps one websocket open for the lifetime of the app: snapshots arrive as
    the server pushes them, and commands travel back over the same socket, so
    nothing has to be polled. Reconnects on its own if the server goes away.
    """

    def __init__(
        self,
        url: str,
        on_snapshot: SnapshotCallback,
        on_status: StatusCallback | None = None,
        reconnect_delay: float = 3.0,
        request_timeout: float = 20.0,
    ) -> None:
        self._url = url
        self._on_snapshot = on_snapshot
        self._on_status = on_status
        self._reconnect_delay = reconnect_delay
        self._request_timeout = request_timeout
        self._websocket: websockets.ClientConnection | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._closed = False

    @property
    def connected(self) -> bool:
        return self._websocket is not None

    async def run(self) -> None:
        """Stay connected until `aclose()`; call this once as a background task."""
        while not self._closed:
            reason = "stream closed"
            try:
                async with websockets.connect(self._url) as websocket:
                    self._websocket = websocket
                    await self._emit_status(True, "connected")
                    async for raw in websocket:
                        self._dispatch(raw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                reason = str(exc) or exc.__class__.__name__
            finally:
                self._websocket = None
                self._fail_pending(ConnectionError("State stream disconnected"))

            if self._closed:
                break
            await self._emit_status(False, reason)
            await asyncio.sleep(self._reconnect_delay)

    async def request(self, action: str, **params: Any) -> dict[str, Any]:
        """Run one command on the server and wait for its result."""
        websocket = self._websocket
        if websocket is None:
            raise ConnectionError("Not connected to the state stream")

        request_id = uuid.uuid4().hex
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            await websocket.send(
                Command(action=action, id=request_id, params=params).model_dump_json()
            )
            return await asyncio.wait_for(future, timeout=self._request_timeout)
        finally:
            self._pending.pop(request_id, None)

    async def aclose(self) -> None:
        self._closed = True
        websocket = self._websocket
        if websocket is not None:
            try:
                await websocket.close()
            except Exception:
                pass

    def _dispatch(self, raw: str | bytes) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("State stream sent invalid JSON")
            return

        message_type = payload.get("type")
        if message_type == StreamMessageType.STATE.value:
            self._call(self._on_snapshot, payload.get("data") or {})
            return

        if message_type != StreamMessageType.RESULT.value:
            logger.warning("Unknown state stream message: %s", message_type)
            return

        future = self._pending.pop(payload.get("id") or "", None)
        if future is None or future.done():
            return
        if payload.get("ok"):
            future.set_result(payload.get("data") or {})
        else:
            future.set_exception(CommandError(payload.get("error") or "Command failed"))

    def _fail_pending(self, error: Exception) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(error)
        self._pending.clear()

    async def _emit_status(self, connected: bool, message: str) -> None:
        if self._on_status is None:
            return
        await self._call_async(self._on_status, connected, message)

    def _call(self, callback: Callable[..., Any], *args: Any) -> None:
        # A consumer that blows up rendering a snapshot must not take the
        # socket down with it.
        try:
            result = callback(*args)
        except Exception as exc:
            logger.error("State stream callback failed: %s", exc)
            return
        if asyncio.iscoroutine(result):
            asyncio.create_task(result)

    async def _call_async(self, callback: Callable[..., Any], *args: Any) -> None:
        result = callback(*args)
        if asyncio.iscoroutine(result):
            await result
