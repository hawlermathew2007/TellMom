import logging
import json
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from shared.schemas.response import ResponseStatus
from proxy.core.jwt import decode_stream_token
from proxy.routers import auth, session
from proxy.services.session import (
    handle_server_message,
    register_server,
    server_map,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        first_message = await websocket.receive_text()
        payload = json.loads(first_message)
        # TODO: replace this one with enum also
        if payload.get("type") != "auth":
            raise ValueError("First message must be of type 'auth'")
        token = payload["token"]
    except (json.JSONDecodeError, KeyError, ValueError):
        await websocket.close(code=4400, reason="Broken auth message.")
        return

    try:
        server_id = decode_stream_token(token)["sub"]
    except HTTPException:
        await websocket.close(code=4401, reason="Invalid token")
        return

    await register_server(server_id, websocket)
    # TODO: put the enum else where
    await websocket.send_text(json.dumps({"type": ResponseStatus.SUCCESS.value}))

    try:
        while True:
            raw = await websocket.receive_text()
            await handle_server_message(raw)
    except WebSocketDisconnect:
        logger.info("Server websocket disconnected: %s", server_id)
    finally:
        server_map.pop(server_id, None)


app = FastAPI(title="TellMom Proxy Server")
app.include_router(auth.router)
app.include_router(session.router)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
