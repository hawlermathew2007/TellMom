import threading
import time
import asyncio
import json

import httpx
import base64
from proxy.database.session import init_db as proxy_init_db
import uvicorn

from backend.services.proxy_agent import ProxyAgent, ProxyState
from backend.services import session_security as sec
from shared.schemas.response import ResponseStatus


PORT = 8080
BASE = f"http://127.0.0.1:{PORT}"


def _start_proxy_server() -> tuple[threading.Thread, uvicorn.Server]:
    config = uvicorn.Config("proxy.main:app", host="127.0.0.1", port=PORT, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread, server


def test_full_proxy_roundtrip() -> None:
    # start proxy server
    # ensure proxy DB tables exist before server starts
    proxy_init_db()
    thread, server = _start_proxy_server()

    # wait for server to start
    # TODO: just do the health check instead
    for _ in range(30):
        try:
            r = httpx.get(BASE + "/openapi.json", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Proxy server did not start in time")

    async def scenario() -> None:
        agent = ProxyAgent(BASE, "integration-server", "pass")
        await agent.register()
        await agent.connect()

        # set a known password code for the backend agent
        ProxyState.current().password_code = "secret"

        async with httpx.AsyncClient() as client:
            # associate (client -> proxy -> backend)
            resp = await client.post(BASE + "/session/associate", json={
                "server_id": agent.server_id,
                "password_code": "secret",
                "client_id": "client-1",
            })
            assert resp.status_code == 200
            data = resp.json()
            session_id = data.get("session_id")
            assert session_id

            # key exchange: client generates DH key and sends public
            client_priv = sec.generate_dh_private_key()
            client_pub = sec.derive_dh_public_key(client_priv)
            resp = await client.post(BASE + "/session/key-exchange", json={
                "session_id": session_id,
                "client_dh_pubkey": sec.int_to_b64(client_pub),
            })
            assert resp.status_code == 200
            server_pub_b64 = resp.json().get("server_dh_pubkey")
            assert server_pub_b64

            server_pub = sec.b64_to_int(server_pub_b64)
            shared = sec.derive_shared_secret(client_priv, server_pub)
            aes_key, nonce_base, _ = sec.derive_session_keys(shared)

            # send encrypted message
            sequence = 1
            nonce = sec.xor_nonce(nonce_base, sequence)
            payload = json.dumps({
                "platform": "discord",
                "user_id": "user-1",
                "server_id": agent.server_id,
                "message": "hello world",
            }).encode("utf-8")
            aad = f"{session_id}:{sequence}".encode("utf-8")
            ciphertext_b64, tag_b64 = sec.encrypt_message(aes_key, nonce, payload, aad)
            nonce_b64 = (base64.urlsafe_b64encode(nonce).rstrip(b"=")).decode("ascii")

            resp = await client.post(BASE + "/session/message", json={
                "session_id": session_id,
                "sequence": sequence,
                "nonce": nonce_b64,
                "ciphertext": ciphertext_b64,
                "auth_tag": tag_b64,
            })
            assert resp.status_code == 200
            resp_data = resp.json()
            assert resp_data.get("status") == ResponseStatus.SUCCESS.value

    # run async scenario
    asyncio.run(scenario())

    # stop uvicorn server
    server.should_exit = True
    thread.join(timeout=2)
