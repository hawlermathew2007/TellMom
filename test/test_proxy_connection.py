import asyncio
import json

from proxy.services.connection import (
    handle_server_message,
    register_server,
    send_proxy_request,
)


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


async def _run_proxy_roundtrip() -> None:
    websocket = FakeWebSocket()
    await register_server("server-1", websocket)

    task = asyncio.create_task(
        send_proxy_request(
            "server-1",
            {"type": "auth_request", "server_id": "server-1", "password_code": "secret"},
        )
    )

    # Wait for the request to be emitted and inspect it
    await asyncio.sleep(0.1)
    assert websocket.sent, "Expected request to be sent to fake websocket"
    request = json.loads(websocket.sent[0])
    response = {
        "request_id": request["request_id"],
        "status": "ok",
        "session_id": "session-123",
    }
    await handle_server_message(json.dumps(response))
    result = await task
    assert result["status"] == "ok"
    assert result["session_id"] == "session-123"


def test_proxy_request_response_correlation() -> None:
    asyncio.run(_run_proxy_roundtrip())
