from __future__ import annotations

import asyncio
import base64
import json
import logging
import secrets
from pathlib import Path
from typing import Any

import httpx
import websockets

from shared.schemas.tunnel import EncryptedMessage, TunnelRequestTypes, TunnelResponse
from shared.schemas.response import ResponseStatus
from shared.services.security import (
    SessionState,
    b64_to_int,
    derive_dh_public_key,
    derive_shared_secret,
    derive_session_keys,
    generate_dh_private_key,
    int_to_b64,
    encrypt_message,
    decrypt_message,
    xor_nonce,
)
from shared.schemas.messages import (
    AuthResponse,
    DhResponse,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

STATE_PATH = Path(__file__).resolve().parent.parent / "backend_state.json"


class ProxyAgent:
    def __init__(self, proxy_url: str, username: str, password: str, local_url: str):
        self.proxy_url = proxy_url.rstrip("/")
        self.username = username
        self.password = password
        self.local_url = local_url
        self.server_id: str | None = None
        self.access_token: str | None = None
        self.websocket: websockets.ClientConnection | None = None
        self.session_states: dict[str, SessionState] = {}

    async def register(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.proxy_url}/auth/register",
                json={"username": self.username, "password": self.password},
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()

        self.server_id = payload["server_id"]
        self.access_token = payload["access_token"]
        logger.info("Registered server %s on proxy", self.server_id)

    async def login(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.proxy_url}/login",
                json={"username": self.username, "password": self.password},
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()

        self.server_id = payload["server_id"]
        self.access_token = payload["access_token"]
        logger.info("Logged in server %s to proxy", self.server_id)

    async def connect(self) -> None:
        if not self.access_token or not self.server_id:
            raise RuntimeError("Proxy agent is not registered or logged in")

        ws_url = (
            self.proxy_url.replace("http://", "ws://").replace("https://", "wss://")
            + "/stream"
        )
        self.websocket = await websockets.connect(ws_url)
        await self.websocket.send(
            json.dumps({"type": "auth", "token": self.access_token})
        )
        raw = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
        message = json.loads(raw)
        if message.get("type") != ResponseStatus.SUCCESS.value:
            raise RuntimeError("Proxy did not accept websocket authentication")

        logger.info("Connected websocket to proxy for server %s", self.server_id)
        asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        assert self.websocket is not None
        try:
            async for raw in self.websocket:
                await self._handle_proxy_request(json.loads(raw))
        except Exception as exc:
            logger.error("Proxy websocket listener stopped: %s", exc)
        finally:
            self.websocket = None

    async def _handle_proxy_request(self, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        request_id = message.get("request_id")
        if request_id is None:
            logger.warning("Proxy request missing request_id: %s", message)
            return

        handlers: dict[str, Any] = {
            TunnelRequestTypes.ASSOCIATE.value: self._handle_auth_request,
            TunnelRequestTypes.KEY_EXCHANGE.value: self._handle_dh_request,
            TunnelRequestTypes.FORWARD.value: self._handle_forward_request,
        }

        handler = handlers.get(str(message_type))
        if handler is None:
            logger.warning("Unknown proxy request type: %s", message_type)
            return

        asyncio.create_task(self._run_handler(handler, message))

    async def _run_handler(self, handler: Any, message: dict[str, Any]) -> None:
        try:
            await handler(message)
        except Exception as exc:
            logger.error(
                "Error running handler for request %s: %s",
                message.get("request_id"),
                exc,
            )

    # TODO: move the protocol to a share folder, apply the generic protocol handler for both the proxy server
    # and the potential future clients that might need it
    async def _handle_forward_request(self, message: dict[str, Any]) -> None:
        request_id = message["request_id"]
        session_id = message["session_id"]
        method = message.get("method", "GET")
        path = message.get("path", "/")
        query = message.get("query", "")
        headers = message.get("headers", {})

        # NOTE: remove the original content-length due to modification hapenning
        headers.pop("content-length", None)
        body_b64 = message.get("body", "")

        state = self.session_states.get(session_id) if session_id else None
        body_bytes = base64.b64decode(body_b64) if body_b64 else b""

        body = body_bytes.decode()
        msg = EncryptedMessage.model_validate_json(body)

        if state is None:
            tunnel_resp = TunnelResponse(
                request_id=request_id,
                status=400,
                body="Provided sequence number does not match with expected value!",
            )
            await self._send_response(tunnel_resp)
            return

        if state.sequence != msg.sequence:
            tunnel_resp = TunnelResponse(
                request_id=request_id,
                status=400,
                body=f"Provided sequence number does not match with expected value {state.sequence} != {msg.sequence}!",
            )
            await self._send_response(tunnel_resp)
            return

        if state.aes_key is None or state.nonce_base is None:
            tunnel_resp = TunnelResponse(
                request_id=request_id,
                status=400,
                body="User hasn't intitialized dh key exchange yet!",
            )
            await self._send_response(tunnel_resp)
            return

        try:
            aad = f"{session_id}:{state.sequence}".encode()
            body_bytes = decrypt_message(
                aes_key=state.aes_key,
                nonce_base=state.nonce_base,
                encrypted_message=msg,
                aad=aad,
            )
        except Exception as e:
            logger.error("Failed to decrypt forward request: %s", e)

        # Build the full path with query
        url = f"{self.local_url}{path}"
        if query:
            url = f"{url}?{query}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body_bytes,
                    timeout=30.0,
                )

                resp_body = resp.content.decode()
                resp_status = resp.status_code

                state.sequence = state.sequence + 1
                ciphertext = encrypt_message(
                    sequence=state.sequence,
                    aes_key=state.aes_key,
                    nonce_base=state.nonce_base,
                    plaintext=resp_body,
                    session_id=session_id,
                )
                resp_body_bytes = ciphertext.model_dump_json().encode()
                resp_body_b64 = base64.b64encode(resp_body_bytes).decode("ascii")
                resp_status = 200

                tunnel_resp = TunnelResponse(
                    request_id=request_id,
                    status=resp_status,
                    body=resp_body_b64,
                )
                await self._send_response(tunnel_resp)

        except Exception as exc:
            logger.error("Failed to forward request %s: %s", request_id, exc)
            tunnel_resp = TunnelResponse(
                request_id=request_id, status=502, body=f"Error: {exc}"
            )
            await self._send_response(tunnel_resp)

    async def _handle_auth_request(self, message: dict[str, Any]) -> None:
        request_id = message["request_id"]
        session_id = message.get("session_id") or ""

        response = AuthResponse(
            request_id=request_id,
            session_id=session_id,
            status=ResponseStatus.FAILED,
        )

        code = message.get("password_code")
        if code != ProxyState.current().password_code:
            response.status = ResponseStatus.FAILED
            response.reason = "Invalid password code"
            await self._send_response(response)
            return

        session_id = session_id or ProxyState.new_session_id()
        self.session_states[session_id] = SessionState(
            session_id=session_id, status="authenticated"
        )
        response.status = ResponseStatus.SUCCESS
        response.session_id = session_id
        await self._send_response(response)

    async def _handle_dh_request(self, message: dict[str, Any]) -> None:
        request_id = message["request_id"]
        session_id = message["session_id"]
        state = self.session_states.get(session_id)
        response = DhResponse(
            request_id=request_id,
            session_id=session_id,
            status=ResponseStatus.FAILED,
        )

        if state is None or state.status != "authenticated":
            response.status = ResponseStatus.FAILED
            response.reason = "Session not authenticated"
            await self._send_response(response)
            return

        client_pub_b64 = message.get("client_dh_pubkey")
        try:
            client_pub = b64_to_int(str(client_pub_b64))
        except Exception:
            response.status = ResponseStatus.FAILED
            response.reason = "Invalid client DH public key"
            await self._send_response(response)
            return

        server_private = generate_dh_private_key()
        server_public = derive_dh_public_key(server_private)
        shared_secret = derive_shared_secret(server_private, client_pub)
        aes_key, nonce_base, _ = derive_session_keys(shared_secret)

        state.server_private = server_private
        state.server_public = server_public
        state.aes_key = aes_key
        state.nonce_base = nonce_base
        state.status = ResponseStatus.SUCCESS.value

        response.status = ResponseStatus.SUCCESS
        response.server_dh_pubkey = int_to_b64(server_public)
        await self._send_response(response)

    async def _send_response(self, response: dict[str, Any] | BaseModel) -> None:
        if self.websocket is None:
            logger.warning("No websocket to send proxy response")
            return
        # accept either a Pydantic model or dict
        if isinstance(response, BaseModel):
            data = response.model_dump()
        else:
            data = dict(response)

        await self.websocket.send(json.dumps(data))


class ProxyState:
    _instance: ProxyState | None = None

    def __init__(self) -> None:
        self.password_code = self._create_password_code()

    @classmethod
    def current(cls) -> ProxyState:
        if cls._instance is None:
            cls._instance = ProxyState()
        return cls._instance

    @classmethod
    def new_session_id(cls) -> str:
        return secrets.token_hex(16)

    @staticmethod
    def _create_password_code() -> str:
        return secrets.token_hex(4)

    @classmethod
    def renew_password_code(cls) -> str:
        instance = cls.current()
        instance.password_code = instance._create_password_code()
        return instance.password_code

    @classmethod
    def serialize(cls) -> dict[str, Any]:
        instance = cls.current()
        return {"password_code": instance.password_code}

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> None:
        instance = cls.current()
        instance.password_code = data.get("password_code", instance.password_code)


def load_state() -> None:
    if STATE_PATH.exists():
        try:
            raw = json.loads(STATE_PATH.read_text())
            ProxyState.deserialize(raw)
        except Exception:
            logger.warning("Unable to load backend state file")


def save_state() -> None:
    STATE_PATH.write_text(json.dumps(ProxyState.serialize(), indent=2))
