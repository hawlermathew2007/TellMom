from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.proxy_agent import ProxyState, save_state, load_state
from backend.services.proxy_manager import proxy_manager

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
    
    proxy_manager.update_config(state.proxy_url, state.username, state.password, state.local_url)
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
    return {
        "status": proxy_manager.status,
        "server_id": proxy_manager.agent.server_id if proxy_manager.agent else None
    }
