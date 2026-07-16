import threading
import time
import asyncio
import json

import httpx
import base64
import uvicorn

from proxy.database.session import init_db as proxy_init_db
from backend.database.session import init_db as backend_init_db
from backend.services.proxy_agent import ProxyAgent, ProxyState
from backend.services import session_security as sec


def _wait_server(url: str):
    for _ in range(10):
        try:
            r = httpx.get(url + "/openapi.json", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception as e:
            print(e)
            time.sleep(1)
    else:
        raise RuntimeError(f"Server {url} did not start in time")


def _start_server(
    path: str, host: str, port: int, log_level: str = "info"
) -> tuple[threading.Thread, uvicorn.Server]:
    config = uvicorn.Config(path, host=host, port=port, log_level=log_level)
    server = uvicorn.Server(config)

    def run():
        try:
            server.run()
        except Exception:
            import traceback

            traceback.print_exc()
            raise

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, server


def test_full_proxy_roundtrip() -> None:
    # start proxy server
    # ensure proxy DB tables exist before server starts
    proxy_init_db()
    backend_init_db()

    P_HOST, P_PORT = "localhost", 8000
    P_URL = f"http://{P_HOST}:{P_PORT}"
    p_thread, p_server = _start_server("proxy.main:app", host=P_HOST, port=P_PORT)

    B_HOST, B_PORT = "localhost", 8080
    B_URL = f"http://{B_HOST}:{B_PORT}"
    b_thread, b_server = _start_server(
        "backend.main:app", host=B_HOST, port=B_PORT, log_level="debug"
    )

    _wait_server(P_URL)
    _wait_server(B_URL)

    async def scenario() -> None:
        agent = ProxyAgent(P_URL, "integration-server", "pass", B_URL)
        await agent.register()
        await agent.connect()

        # set a known password code for the backend agent
        ProxyState.current().password_code = "secret"

        async with httpx.AsyncClient() as client:
            # associate (client -> proxy -> backend)
            # TODO: make the user register to associate also
            resp = await client.post(
                P_URL + "/session/associate",
                json={
                    "server_id": agent.server_id,
                    "password_code": "secret",
                    "client_id": "client-1",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            session_id = data.get("session_id")
            assert session_id

            # key exchange: client generates DH key and sends public
            client_priv = sec.generate_dh_private_key()
            client_pub = sec.derive_dh_public_key(client_priv)
            resp = await client.post(
                P_URL + "/session/key-exchange",
                json={
                    "session_id": session_id,
                    "client_dh_pubkey": sec.int_to_b64(client_pub),
                },
            )
            assert resp.status_code == 200
            server_pub_b64 = resp.json().get("server_dh_pubkey")
            assert server_pub_b64

            server_pub = sec.b64_to_int(server_pub_b64)
            shared = sec.derive_shared_secret(client_priv, server_pub)
            aes_key, nonce_base, _ = sec.derive_session_keys(shared)

            sequence = 1
            nonce = sec.xor_nonce(nonce_base, sequence)
            payload = json.dumps(
                {
                    "platform": "discord",
                    "user_id": "user-1",
                    "server_id": "server-1",
                    "message": "hello tunnel",
                }
            ).encode("utf-8")
            aad = f"{session_id}:{sequence}".encode("utf-8")
            ciphertext_b64, tag_b64 = sec.encrypt_message(aes_key, nonce, payload, aad)
            nonce_b64 = (base64.urlsafe_b64encode(nonce).rstrip(b"=")).decode("ascii")

            encrypted_body = json.dumps(
                {
                    "sequence": sequence,
                    "nonce": nonce_b64,
                    "ciphertext": ciphertext_b64,
                    "auth_tag": tag_b64,
                }
            ).encode()

            resp = await client.post(
                P_URL + f"/session/{session_id}/forward/message/ingest",
                content=encrypted_body,
                headers={"content-type": "application/json"},
            )
            print(resp.json())
            assert resp.status_code == 200
            # resp_data = resp.json()
            # assert resp_data.get("status") == "success"

    # run async scenario
    asyncio.run(scenario())

    # stop uvicorn server
    p_server.should_exit = True
    b_server.should_exit = True
    p_thread.join(timeout=2)
    b_thread.join(timeout=2)
