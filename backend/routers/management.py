import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.proxy_agent import ProxyState, save_state, load_state
from backend.services.proxy_manager import proxy_manager
from backend.services.classifier_stream import classifier_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/management", tags=["management"])


class ConfigUpdate(BaseModel):
    proxy_url: str
    username: str
    password: str
    local_url: str


@router.get("/state")
async def get_state():
    load_state()
    return ProxyState.serialize()


@router.post("/state")
async def update_state(data: ConfigUpdate):
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


@router.post("/renew_passcode")
async def renew_passcode():
    new_code = ProxyState.renew_password_code()
    save_state()
    return {"passcode": new_code}


@router.post("/register")
async def register():
    try:
        await proxy_manager.register()
        return {"status": "registered", "server_id": proxy_manager.agent.server_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login():
    try:
        await proxy_manager.login()
        return {"status": "logged_in", "server_id": proxy_manager.agent.server_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect():
    try:
        await proxy_manager.connect()
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def status():
    current_status = proxy_manager.status
    if proxy_manager.agent and proxy_manager.agent.status in [
        "reconnecting",
        "connecting",
        "disconnected",
        "login_failed",
    ]:
        if current_status not in ["Login Failed", "Connect Failed", "Config Missing"]:
            current_status = proxy_manager.agent.status.replace("_", " ").title()

    return {
        "status": current_status,
        "classifier_status": "Connected"
        if classifier_stream.connected
        else "Disconnected",
        "server_id": proxy_manager.agent.server_id if proxy_manager.agent else None,
    }
