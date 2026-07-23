import asyncio
import json
import logging
import base64
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

active_ws_connections: dict[str, WebSocket] = {}


def register_ws_connection(connection_id: str, ws: WebSocket) -> None:
    active_ws_connections[connection_id] = ws


def get_ws_connection(connection_id: str) -> WebSocket | None:
    return active_ws_connections.get(connection_id)


def unregister_ws_connection(connection_id: str) -> None:
    active_ws_connections.pop(connection_id, None)


def associate_session(session_id: str, server_id: str) -> None:
    session_map[session_id] = server_id


def get_server_for_session(session_id: str) -> str | None:
    return session_map.get(session_id)


async def register_server(server_id: str, websocket: WebSocket) -> None:
    logger.info("Registering server %s", server_id)
    server_map[server_id] = websocket


async def send_proxy_request(
    server_id: str, payload: BaseModel | dict[str, Any]
) -> dict[str, Any]:
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
        raise RuntimeError(
            f"Failed to send request to server {server_id}: {exc}"
        ) from exc

    try:
        return await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            f"Timed out waiting for server {server_id} response"
        ) from exc
    finally:
        async with pending_lock:
            pending_requests.pop(request_id, None)


async def send_proxy_ws_message(server_id: str, message: dict[str, Any]) -> None:
    websocket = server_map.get(server_id)
    if websocket is None:
        raise RuntimeError(f"Server {server_id} is not connected")
    try:
        await websocket.send_text(json.dumps(message))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to send ws message to server {server_id}: {exc}"
        ) from exc


async def handle_server_message(raw: str) -> None:
    message = _parse_message(raw)
    if message is None:
        return

    request_id = message.get("request_id")
    if request_id is None:
        await _handle_unsolicited_message(message)
        return

    await _resolve_pending_request(request_id, message)


def _parse_message(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Received invalid JSON from server: %s", raw)
        return None


async def _handle_unsolicited_message(message: dict) -> None:
    msg_type = message.get("type")

    if msg_type in {"ws_frame", "ws_close"}:
        await _handle_ws_message(message)
        return

    logger.warning("Server response missing request_id: %s", message)


async def _handle_ws_message(message: dict) -> None:
    connection_id = message.get("connection_id")
    if not connection_id:
        return

    ws = get_ws_connection(connection_id)
    if ws is None:
        return

    msg_type = message["type"]

    if msg_type == "ws_frame":
        await _forward_ws_frame(ws, message)
    elif msg_type == "ws_close":
        await _close_ws(ws, connection_id, message)


async def _forward_ws_frame(ws, message: dict) -> None:
    opcode = message.get("opcode")
    data = message.get("data", "")

    if opcode == "text":
        await ws.send_text(data)
        return

    if opcode == "binary":
        await ws.send_bytes(base64.b64decode(data))
        return


async def _close_ws(ws, connection_id: str, message: dict) -> None:
    await ws.close(code=message.get("code", 1000))
    unregister_ws_connection(connection_id)


async def _resolve_pending_request(request_id: str, message: dict) -> None:
    async with pending_lock:
        future = pending_requests.get(request_id)

        if future is None:
            logger.warning(
                "No pending proxy request matches request_id=%s",
                request_id,
            )
            return

        if not future.done():
            future.set_result(message)
