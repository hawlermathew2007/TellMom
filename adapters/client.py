from __future__ import annotations

import base64
import json
import logging

import httpx
from shared.schemas.response import ResponseStatus
from shared.services.security import (
    generate_dh_private_key,
    derive_dh_public_key,
    derive_shared_secret,
    derive_session_keys,
    encrypt_message,
    decrypt_message,
    int_to_b64,
    b64_to_int,
)

log = logging.getLogger("tellmom.client")


class SecureProxyClient:
    def __init__(
        self,
        proxy_url: str,
        server_id: str,
        password_code: str,
        client_id: str | None = None,
        timeout: float = 10.0,
    ):
        self.proxy_url = proxy_url.rstrip("/")
        self.server_id = server_id
        self.password_code = password_code
        self.client_id = client_id or "client"
        self._client = httpx.AsyncClient(timeout=timeout)
        self.session_id: str | None = None
        self.aes_key: bytes | None = None
        self.nonce_base: bytes | None = None
        self.sequence = 0
        self.client_private = None

    async def _authenticate(self) -> None:
        payload = {
            "server_id": self.server_id,
            "password_code": self.password_code,
            "client_id": self.client_id,
        }
        response = await self._client.post(
            f"{self.proxy_url}/session/auth", json=payload
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != ResponseStatus.SUCCESS.value or not data.get("session_id"):
            raise RuntimeError(data.get("reason", "Authentication failed"))
        self.session_id = data["session_id"]

    async def _exchange_dh(self) -> None:
        self.client_private = generate_dh_private_key()
        client_pub = derive_dh_public_key(self.client_private)
        response = await self._client.post(
            f"{self.proxy_url}/session/dh",
            json={
                "session_id": self.session_id,
                "client_dh_pubkey": int_to_b64(client_pub),
            },
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != ResponseStatus.SUCCESS.value:
            raise RuntimeError(data.get("reason", "DH exchange failed"))

        server_pub = b64_to_int(data["server_dh_pubkey"])
        shared_secret = derive_shared_secret(self.client_private, server_pub)
        self.aes_key, self.nonce_base, _ = derive_session_keys(shared_secret)

    async def ensure_handshake(self) -> None:
        if self.session_id is None:
            await self._authenticate()
        if self.aes_key is None or self.nonce_base is None:
            await self._exchange_dh()

    async def send(self, payload: dict) -> None:
        await self.ensure_handshake()
        assert self.session_id is not None
        assert self.aes_key is not None and self.nonce_base is not None

        self.sequence += 1
        encrypted_message = encrypt_message(
            sequence=self.sequence,
            aes_key=self.aes_key,
            nonce_base=self.nonce_base,
            plaintext=json.dumps(payload),
            session_id=self.session_id,
        )

        response = await self._client.post(
            f"{self.proxy_url}/session/{self.session_id}/message",
            json=encrypted_message,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != ResponseStatus.SUCCESS.value:
            raise RuntimeError(data.get("reason", "Encrypted message rejected"))

        server_sequence = data.get("sequence")
        server_nonce_str = data.get("nonce", "")
        server_nonce = base64.urlsafe_b64decode(
            server_nonce_str + "=" * (-len(server_nonce_str) % 4)
        )
        decrypt_message(
            self.aes_key,
            server_nonce,
            data.get("ciphertext", ""),
            data.get("auth_tag", ""),
            f"{self.session_id}:{server_sequence}".encode("utf-8"),
        )

    async def aclose(self) -> None:
        await self._client.aclose()


class IngestClient:
    def __init__(
        self,
        backend_url: str | None,
        server_id: str,
        proxy_url: str,
        timeout: float = 10.0,
        password_code: str | None = None,
        client_id: str | None = None,
    ):
        self.backend_url = backend_url
        self.server_id = server_id
        self.proxy_url = proxy_url
        self.password_code = password_code or ""
        self._timeout = timeout
        self._client = (
            SecureProxyClient(
                proxy_url,
                server_id,
                self.password_code,
                client_id=client_id,
                timeout=timeout,
            )
            if proxy_url
            else None
        )
        self._backend_client = httpx.AsyncClient(timeout=timeout)

    async def send(self, payload: dict) -> None:
        if self._client is not None:
            await self._client.send(payload)
            return

        assert self.backend_url is not None
        resp = await self._backend_client.post(self.backend_url, json=payload)
        resp.raise_for_status()

    async def send_with_retry(self, payload: dict, max_retries: int = 5) -> None:
        import asyncio

        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                await self.send(payload)
                return
            except httpx.HTTPStatusError as exc:
                if 400 <= exc.response.status_code < 500:
                    log.error(
                        "Backend rejected message (status %d): %s",
                        exc.response.status_code,
                        exc.response.text,
                    )
                    return
                log.warning(
                    "Server error sending message (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    exc,
                )
            except httpx.HTTPError as exc:
                log.warning(
                    "Network error sending message (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    exc,
                )

            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
        log.error("Giving up on message after %d attempts", max_retries)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        if self._backend_client is not None:
            await self._backend_client.aclose()
