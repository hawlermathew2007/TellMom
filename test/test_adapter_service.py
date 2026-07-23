import asyncio
import threading
import time

import httpx
import uvicorn

from adapters.platforms import ChatPlatform
from backend.schemas.ingest import IngestRequest
from proxy.database.session import init_db as proxy_init_db
from backend.database.session import init_db as backend_init_db
from backend.services.proxy_agent import ProxyAgent, ProxyState


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
    b_thread, b_server = _start_server("backend.main:app", host=B_HOST, port=B_PORT)

    A_HOST, A_PORT = "localhost", 8001
    A_URL = f"http://{A_HOST}:{A_PORT}"
    a_thread, a_server = _start_server(
        "adapters.server:app", host=A_HOST, port=A_PORT, log_level="debug"
    )

    _wait_server(P_URL)
    _wait_server(B_URL)
    _wait_server(A_URL)

    async def scenario() -> None:
        agent = ProxyAgent(P_URL, "integration-server", "pass", B_URL)
        await agent.register()
        await agent.connect()

        # set a known password code for the backend agent
        ProxyState.current().password_code = "secret"

        async with httpx.AsyncClient() as client:
            # Connecting the adapter server to the proxy server
            resp = await client.post(
                A_URL + "/api/connection",
                json={
                    "proxy_url": P_URL,
                    "server_id": agent.server_id,
                    "password_code": "secret",
                },
            )
            assert resp.status_code == 200

            payload = IngestRequest(
                platform=ChatPlatform.DISCORD,
                user_id="user-1",
                server_id="server-1",
                message="hello tunnel",
            )
            resp = await client.post(A_URL + "/ingest", json=payload.model_dump())
            assert resp.status_code == 200

    # run async scenario
    asyncio.run(scenario())

    # stop uvicorn server
    p_server.should_exit = True
    b_server.should_exit = True
    a_server.should_exit = True
    p_thread.join(timeout=2)
    b_thread.join(timeout=2)
    a_thread.join(timeout=2)
