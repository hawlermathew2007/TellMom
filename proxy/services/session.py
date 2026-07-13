import asyncio
import json
import logging
import uuid
from typing import Any
from pydantic import BaseModel

from fastapi import WebSocket

logger = logging.getLogger(__name__)

server_map: dict[str, WebSocket] = {}
# TODO: turn this into TTL dict instead 
session_map: dict[str, str] = {}
pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}
pending_lock = asyncio.Lock()


def associate_session(session_id: str, server_id: str) -> None:
    session_map[session_id] = server_id


def get_server_for_session(session_id: str) -> str | None:
    return session_map.get(session_id)


async def register_server(server_id: str, websocket: WebSocket) -> None:
    logger.info("Registering server %s", server_id)
    server_map[server_id] = websocket


async def send_proxy_request(server_id: str, payload: BaseModel | dict[str, Any]) -> dict[str, Any]:
    websocket = server_map.get(server_id)
    if websocket is None:
        raise RuntimeError(f"Server {server_id} is not connected")

    # allow either a pydantic model or raw dict
    if isinstance(payload, BaseModel):
        data = payload.model_dump()
    else:
        data = dict(payload)

    request_id = data.get("request_id") or str(uuid.uuid4())
    data["request_id"] = request_id

    loop = asyncio.get_running_loop()
    future: asyncio.Future[dict[str, Any]] = loop.create_future()

    async with pending_lock:
        pending_requests[request_id] = future

    try:
        await websocket.send_text(json.dumps(data))
    except Exception as exc:
        raise RuntimeError(f"Failed to send request to server {server_id}: {exc}") from exc

    try:
        return await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Timed out waiting for server {server_id} response") from exc
    finally:
        async with pending_lock:
            pending_requests.pop(request_id, None)


async def handle_server_message(raw: str) -> None:
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Received invalid JSON from server: %s", raw)
        return

    request_id = message.get("request_id")
    if request_id is None:
        logger.warning("Server response missing request_id: %s", message)
        return

    async with pending_lock:
        future = pending_requests.get(request_id)
        if future is None:
            logger.warning("No pending proxy request matches request_id=%s", request_id)
            return
        if not future.done():
            future.set_result(message)
