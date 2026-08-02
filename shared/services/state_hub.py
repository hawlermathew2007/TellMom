from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Awaitable, Callable

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from shared.schemas.stream import Command, CommandResult, StateEvent

logger = logging.getLogger(__name__)

SnapshotFn = Callable[[], dict[str, Any] | Awaitable[dict[str, Any]]]
CommandHandler = Callable[[str, dict[str, Any]], Any]

# Only the newest snapshot matters, so a short queue is enough; a client that
# falls behind gets the stale entries dropped rather than blocking the server.
QUEUE_SIZE = 8


class StateHub:
    """Server side of a state stream: pushes snapshots instead of being polled.

    A subscriber receives a snapshot when it connects and afterwards only when
    the snapshot actually differs from the last one broadcast. `publish()` is
    called right after a mutation, and by `run_watcher()` for the state that
    changes on its own (an adapter subprocess dying, a proxy socket dropping).
    """

    def __init__(self, snapshot_fn: SnapshotFn, poll_interval: float = 1.0) -> None:
        self._snapshot_fn = snapshot_fn
        self._poll_interval = poll_interval
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._last: dict[str, Any] | None = None

    async def snapshot(self) -> dict[str, Any]:
        result = self._snapshot_fn()
        if inspect.isawaitable(result):
            result = await result
        return result

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, force: bool = False) -> dict[str, Any]:
        snapshot = await self.snapshot()
        if snapshot == self._last and not force:
            return snapshot

        self._last = snapshot
        for queue in list(self._subscribers):
            self._offer(queue, snapshot)
        return snapshot

    async def run_watcher(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._poll_interval)
                if self._subscribers:
                    await self.publish()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("State hub watcher error: %s", exc)

    @staticmethod
    def _offer(queue: asyncio.Queue[dict[str, Any]], snapshot: dict[str, Any]) -> None:
        while True:
            try:
                queue.put_nowait(snapshot)
                return
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    return


async def serve_state_stream(
    hub: StateHub,
    websocket: WebSocket,
    handler: CommandHandler | None = None,
) -> None:
    """Run one client connection: push snapshots out, run commands coming in."""
    await websocket.accept()
    # Subscribe before the first snapshot so a change in between is queued,
    # not lost.
    queue = hub.subscribe()
    try:
        initial = await hub.snapshot()
        await _send(websocket, StateEvent(data=initial))

        tasks = [
            asyncio.create_task(_push_snapshots(websocket, queue, initial)),
            asyncio.create_task(_run_commands(hub, websocket, handler)),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            error = task.exception()
            if error is not None and not isinstance(error, WebSocketDisconnect):
                logger.error("State stream ended with an error: %s", error)
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(queue)


async def _push_snapshots(
    websocket: WebSocket,
    queue: asyncio.Queue[dict[str, Any]],
    last_sent: dict[str, Any],
) -> None:
    while True:
        snapshot = await queue.get()
        # This connection may already have the snapshot: it was sent one on
        # connect, and a command it ran publishes the result to everyone.
        if snapshot == last_sent:
            continue
        last_sent = snapshot
        await _send(websocket, StateEvent(data=snapshot))


async def _run_commands(
    hub: StateHub, websocket: WebSocket, handler: CommandHandler | None
) -> None:
    while True:
        raw = await websocket.receive_text()
        await _send(websocket, await _run_command(raw, handler))
        # A command almost always moved the state; let every subscriber see it.
        await hub.publish()


async def _run_command(raw: str, handler: CommandHandler | None) -> CommandResult:
    try:
        command = Command.model_validate_json(raw)
    except ValidationError as exc:
        return CommandResult(ok=False, error=f"Malformed command: {exc}")

    if handler is None:
        return CommandResult(
            ok=False,
            id=command.id,
            action=command.action,
            error="This stream does not accept commands",
        )

    try:
        result = handler(command.action, command.params)
        if inspect.isawaitable(result):
            result = await result
    except Exception as exc:
        logger.error("Command '%s' failed: %s", command.action, exc)
        return CommandResult(
            ok=False, id=command.id, action=command.action, error=str(exc)
        )

    return CommandResult(
        ok=True, id=command.id, action=command.action, data=result or {}
    )


async def _send(websocket: WebSocket, message: StateEvent | CommandResult) -> None:
    await websocket.send_text(message.model_dump_json())
