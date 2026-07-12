import logging
import json
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket

from proxy.core.jwt import decode_stream_token
from proxy.schemas.auth import SocketCodes
from proxy.routers import auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_map: dict[str, WebSocket] = {}
router = APIRouter()


@router.websocket("/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        first_message = await websocket.receive_text()
        payload = json.loads(first_message)
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

    # TODO: turn this into a TTL and allow token refresh also
    server_map[server_id] = websocket

    # Let the local server know that authentication done
    await websocket.send_text(json.dumps({"type": SocketCodes.AUTH_OK}))

    # TODO: write the websocket processor here
    # TODO: now the one delivering the message gotta be the proxy
    # await router.connect(websocket)
    # try:
    #     while True:
    #         raw = await websocket.receive_text()
    #         router.handle_message(raw)
    # except WebSocketDisconnect:
    #     classifier_stream.disconnect()


app = FastAPI(title="TellMom Proxy Server")
app.include_router(auth.router)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
