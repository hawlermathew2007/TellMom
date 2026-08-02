import logging
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel

from backend.services.proxy_agent import ProxyState, save_state
from backend.services.proxy_manager import proxy_manager
from backend.services.status_hub import management_hub
from shared.services.state_hub import serve_state_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/management", tags=["management"])


class ConfigUpdate(BaseModel):
    proxy_url: str
    username: str
    password: str
    local_url: str


async def apply_config(data: ConfigUpdate) -> dict[str, str]:
    state = ProxyState.current()
    state.proxy_url = data.proxy_url
    state.username = data.username
    state.password = data.password
    state.local_url = data.local_url
    save_state()

    await proxy_manager.update_config(
        state.proxy_url, state.username, state.password, state.local_url
    )

    return {"status": "ok"}


def _server_id() -> str | None:
    return proxy_manager.agent.server_id if proxy_manager.agent else None


async def register_agent() -> dict[str, Any]:
    await proxy_manager.register()
    return {"status": "registered", "server_id": _server_id()}


async def login_agent() -> dict[str, Any]:
    await proxy_manager.login()
    return {"status": "logged_in", "server_id": _server_id()}


async def connect_agent() -> dict[str, Any]:
    await proxy_manager.connect()
    return {"status": "connected"}


def renew_passcode_value() -> dict[str, str]:
    new_code = ProxyState.renew_password_code()
    save_state()
    return {"passcode": new_code}


COMMANDS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "set_config": lambda params: apply_config(ConfigUpdate.model_validate(params)),
    "register": lambda _: register_agent(),
    "login": lambda _: login_agent(),
    "connect": lambda _: connect_agent(),
    "renew_passcode": lambda _: renew_passcode_value(),
}


def handle_command(action: str, params: dict[str, Any]) -> Any:
    command = COMMANDS.get(action)
    if command is None:
        raise ValueError(f"Unknown management action: {action}")
    return command(params)


@router.websocket("/ws")
async def management_stream(websocket: WebSocket) -> None:
    """Live status/config feed, and the channel every management action runs on."""
    await serve_state_stream(management_hub, websocket, handle_command)


@router.post("/state")
async def update_state(data: ConfigUpdate):
    result = await apply_config(data)
    await management_hub.publish()
    return result


@router.post("/renew_passcode")
async def renew_passcode():
    result = renew_passcode_value()
    await management_hub.publish()
    return result


@router.post("/register")
async def register():
    try:
        result = await register_agent()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    await management_hub.publish()
    return result


@router.post("/login")
async def login():
    try:
        result = await login_agent()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    await management_hub.publish()
    return result


@router.post("/connect")
async def connect():
    try:
        result = await connect_agent()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    await management_hub.publish()
    return result
