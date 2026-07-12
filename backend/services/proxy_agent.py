from __future__ import annotations

import asyncio
import base64
import json
import logging
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import websockets

from core.registry import ChatPlatform
from services.session_security import (
    SessionState,
    b64_to_int,
    decrypt_message,
    derive_dh_public_key,
    derive_shared_secret,
    derive_session_keys,
    encrypt_message,
    generate_dh_private_key,
    int_to_b64,
    xor_nonce,
)
from database.session import SessionLocal
from services.ingest import process_ingest

logger = logging.getLogger(__name__)

STATE_PATH = Path(__file__).resolve().parent.parent / "backend_state.json"


# TODO: move the shared schemas outside so this one can use also
@dataclass
class ProxyRegistrationState:
    proxy_url: str
    username: str
    password: str
    server_id: str | None = None
    access_token: str | None = None


class ProxyAgent:
    def __init__(self, proxy_url: str, username: str, password: str):
        self.proxy_url = proxy_url.rstrip("/")
        self.username = username
        self.password = password
        self.server_id: str | None = None
        self.access_token: str | None = None
        self.websocket: websockets.ClientConnection | None = None
        self.session_states: dict[str, SessionState] = {}

    async def register(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.proxy_url}/register",
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
        if message.get("type") != "SUCCESS":
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

        if message_type == "ASSOCIATE":
            await self._handle_auth_request(message)
        elif message_type == "KEY_EXCHANGE":
            await self._handle_dh_request(message)
        elif message_type == "MESSAGE":
            await self._handle_encrypted_message(message)
        else:
            logger.warning("Unknown proxy request type: %s", message_type)

    async def _handle_auth_request(self, message: dict[str, Any]) -> None:
        request_id = message["request_id"]
        session_id = message.get("session_id") or ""
        response = {
            "type": "auth_response",
            "request_id": request_id,
            "session_id": session_id,
        }

        code = message.get("password_code")
        if code != ProxyState.current().password_code:
            response["status"] = "FAILED"
            response["reason"] = "Invalid password code"
            await self._send_response(response)
            return

        session_id = session_id or ProxyState.new_session_id()
        # TODO: move this to enum also
        self.session_states[session_id] = SessionState(
            session_id=session_id, status="authenticated"
        )
        response["status"] = "SUCCESS"
        response["session_id"] = session_id
        await self._send_response(response)

    async def _handle_dh_request(self, message: dict[str, Any]) -> None:
        request_id = message["request_id"]
        session_id = message["session_id"]
        state = self.session_states.get(session_id)
        response = {
            "type": "dh_response",
            "request_id": request_id,
            "session_id": session_id,
        }

        if state is None or state.status != "authenticated":
            response["status"] = "failed"
            response["reason"] = "Session not authenticated"
            await self._send_response(response)
            return

        client_pub_b64 = message.get("client_dh_pubkey")
        try:
            client_pub = b64_to_int(str(client_pub_b64))
        except Exception:
            response["status"] = "failed"
            response["reason"] = "Invalid client DH public key"
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
        state.status = "ready"
        state.client_sequence = 0
        state.server_sequence = 0

        response["status"] = "ok"
        response["server_dh_pubkey"] = int_to_b64(server_public)
        await self._send_response(response)

    async def _handle_encrypted_message(self, message: dict[str, Any]) -> None:
        request_id = message["request_id"]
        session_id = message["session_id"]
        state = self.session_states.get(session_id)
        response = {
            "type": "message_response",
            "request_id": request_id,
            "session_id": session_id,
        }

        if state is None or state.status != "ready":
            response["status"] = "failed"
            response["reason"] = "Session not ready"
            await self._send_response(response)
            return

        sequence = int(message.get("sequence", -1))
        # TODO: the nonce is not yet used because there's no request from parent client to fetch data yet
        # nonce = message.get("nonce")
        ciphertext = message.get("ciphertext")
        auth_tag = message.get("auth_tag")
        aad = f"{session_id}:{sequence}".encode("utf-8")

        if sequence != state.client_sequence + 1:
            response["status"] = "failed"
            response["reason"] = "Invalid sequence"
            await self._send_response(response)
            return

        try:
            plaintext = decrypt_message(
                state.aes_key,
                xor_nonce(state.nonce_base, sequence),
                ciphertext,
                auth_tag,
                aad,
            )
            payload = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            logger.warning("Failed to decrypt client payload: %s", exc)
            response["status"] = "failed"
            response["reason"] = "Invalid encrypted payload"
            await self._send_response(response)
            return

        state.client_sequence = sequence

        try:
            ingest_result = await self._process_request(payload)
        except Exception as exc:
            logger.warning("Ingest processing failed: %s", exc)
            response["status"] = "failed"
            response["reason"] = str(exc)
            await self._send_response(response)
            return

        response_payload = json.dumps({"status": "ok", "result": ingest_result}).encode(
            "utf-8"
        )

        state.server_sequence += 1
        server_sequence = state.server_sequence
        server_nonce = xor_nonce(state.nonce_base, server_sequence)
        ciphertext_b64, tag_b64 = encrypt_message(
            state.aes_key,
            server_nonce,
            response_payload,
            f"{session_id}:{server_sequence}".encode("utf-8"),
        )

        response.update(
            {
                "status": "ok",
                "sequence": server_sequence,
                "nonce": base64.urlsafe_b64encode(server_nonce)
                .rstrip(b"=")
                .decode("ascii"),
                "ciphertext": ciphertext_b64,
                "auth_tag": tag_b64,
            }
        )
        await self._send_response(response)

    async def _process_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        platform_raw = payload.get("platform")
        user_id = payload.get("user_id")
        server_id = payload.get("server_id")
        message = payload.get("message")
        if not all([platform_raw, user_id, server_id, message]):
            raise ValueError("Invalid ingest payload")

        platform = ChatPlatform(platform_raw)
        with SessionLocal() as db:
            await process_ingest(db, platform, user_id, server_id, message)

        return {"ingested": True}

    async def _send_response(self, response: dict[str, Any]) -> None:
        if self.websocket is None:
            logger.warning("No websocket to send proxy response")
            return
        await self.websocket.send(json.dumps(response))


class ProxyState:
    _instance: ProxyState | None = None

    def __init__(self) -> None:
        self.password_code = self._create_password_code()

    @classmethod
    def current(cls) -> "ProxyState":
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
