from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("tellmom.client")


class SecureProxyClient:
    DH_P = int(
        "FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1"
        "29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD"
        "EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245"
        "E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED"
        "EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE65381"
        "FFFFFFFF FFFFFFFF",
        16,
    )
    DH_G = 2

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

    @staticmethod
    def _serialize_b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def _deserialize_b64(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    @staticmethod
    def _int_to_b64(value: int) -> str:
        raw = value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64_to_int(value: str) -> int:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        return int.from_bytes(raw, "big")

    def _generate_dh_private_key(self) -> int:
        return secrets.randbelow(self.DH_P - 2) + 2

    def _derive_dh_public_key(self, private_key: int) -> int:
        return pow(self.DH_G, private_key, self.DH_P)

    def _derive_shared_secret(self, private_key: int, peer_public: int) -> bytes:
        shared = pow(peer_public, private_key, self.DH_P)
        secret_bytes = shared.to_bytes((shared.bit_length() + 7) // 8 or 1, "big")
        return hashlib.sha256(secret_bytes).digest()

    def _hkdf_extract(self, salt: bytes, ikm: bytes) -> bytes:
        return hmac.new(salt, ikm, hashlib.sha256).digest()

    def _hkdf_expand(self, prk: bytes, info: bytes, length: int) -> bytes:
        result = b""
        previous = b""
        counter = 1
        while len(result) < length:
            previous = hmac.new(
                prk, previous + info + bytes([counter]), hashlib.sha256
            ).digest()
            result += previous
            counter += 1
        return result[:length]

    def _derive_session_keys(self, shared_secret: bytes) -> tuple[bytes, bytes, bytes]:
        prk = self._hkdf_extract(b"", shared_secret)
        aes_key = self._hkdf_expand(prk, b"aes-gcm", 32)
        nonce_base = self._hkdf_expand(prk, b"nonce", 12)
        future_keys = self._hkdf_expand(prk, b"future", 32)
        return aes_key, nonce_base, future_keys

    @staticmethod
    def _xor_nonce(nonce_base: bytes, sequence: int) -> bytes:
        sequence_bytes = sequence.to_bytes(len(nonce_base), "big")
        return bytes(a ^ b for a, b in zip(nonce_base, sequence_bytes))

    @staticmethod
    def _encrypt(
        aes_key: bytes, nonce: bytes, plaintext: bytes, aad: bytes
    ) -> tuple[str, str]:
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        return (
            base64.urlsafe_b64encode(ciphertext[:-16]).rstrip(b"=").decode("ascii"),
            base64.urlsafe_b64encode(ciphertext[-16:]).rstrip(b"=").decode("ascii"),
        )

    @staticmethod
    def _decrypt(
        aes_key: bytes, nonce: bytes, ciphertext_b64: str, tag_b64: str, aad: bytes
    ) -> bytes:
        ciphertext = base64.urlsafe_b64decode(
            ciphertext_b64 + "=" * (-len(ciphertext_b64) % 4)
        )
        tag = base64.urlsafe_b64decode(tag_b64 + "=" * (-len(tag_b64) % 4))
        aesgcm = AESGCM(aes_key)
        return aesgcm.decrypt(nonce, ciphertext + tag, aad)

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
        if data.get("status") != "ok" or not data.get("session_id"):
            raise RuntimeError(data.get("reason", "Authentication failed"))
        self.session_id = data["session_id"]

    async def _exchange_dh(self) -> None:
        self.client_private = self._generate_dh_private_key()
        client_pub = self._derive_dh_public_key(self.client_private)
        response = await self._client.post(
            f"{self.proxy_url}/session/dh",
            json={
                "session_id": self.session_id,
                "client_dh_pubkey": self._int_to_b64(client_pub),
            },
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            raise RuntimeError(data.get("reason", "DH exchange failed"))

        server_pub = self._b64_to_int(data["server_dh_pubkey"])
        shared_secret = self._derive_shared_secret(self.client_private, server_pub)
        self.aes_key, self.nonce_base, _ = self._derive_session_keys(shared_secret)

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
        nonce = self._xor_nonce(self.nonce_base, self.sequence)
        aad = f"{self.session_id}:{self.sequence}".encode("utf-8")
        ciphertext, auth_tag = self._encrypt(
            self.aes_key,
            nonce,
            json.dumps(payload).encode("utf-8"),
            aad,
        )

        response = await self._client.post(
            f"{self.proxy_url}/session/{self.session_id}/message",
            json={
                "sequence": self.sequence,
                "nonce": self._serialize_b64(nonce),
                "ciphertext": ciphertext,
                "auth_tag": auth_tag,
            },
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            raise RuntimeError(data.get("reason", "Encrypted message rejected"))

        server_sequence = data.get("sequence")
        server_nonce = self._deserialize_b64(data.get("nonce", ""))
        self._decrypt(
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

