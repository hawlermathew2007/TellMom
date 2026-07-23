import asyncio
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks

from adapters.base import AdapterRegistry
from adapters.minecraft.minecraft import plugin as minecraft_plugin
from adapters.client import SecureProxyClient

CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"
BASE_DIR = Path(__file__).resolve().parent

registry = AdapterRegistry()
registry.register(minecraft_plugin)

app = FastAPI()

# Global state
processes: Dict[str, subprocess.Popen] = {}
proxy_client: Optional[SecureProxyClient] = None
connection_info = {
    "proxy_url": None,
    "server_id": None,
    "status": "Disconnected"
}

def load_config() -> Dict[str, Any]:
    cfg = {}
    for adapter in registry.list_adapters():
        cfg[adapter.name] = adapter.default_config.copy()
        
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                user_cfg = yaml.safe_load(f)
            if user_cfg:
                for name, default_val in cfg.items():
                    if name in user_cfg:
                        default_val.update(user_cfg[name])
        except Exception as e:
            print(f"Error loading config: {e}")
    return cfg

@app.on_event("startup")
async def on_startup():
    config = load_config()
    # Check for auto_start
    for name, cfg in config.items():
        if cfg.get("auto_start"):
            start_adapter_internal(name, cfg)

def start_adapter_internal(name: str, cfg: dict):
    if name in processes and processes[name].poll() is None:
        return
    
    adapter = registry.get(name)
    if not adapter:
        return
        
    log_file_path = BASE_DIR / f"{name}_output.log"
    log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")
    
    # Overwrite backend_url to point to this server
    cfg["backend_url"] = "http://127.0.0.1:8000/ingest"
    cfg["proxy_url"] = "" # Disable proxy client inside adapter
    
    proc = adapter.launch(BASE_DIR, cfg, log_file)
    processes[name] = proc

@app.get("/api/adapters")
def list_adapters():
    config = load_config()
    result = []
    for adapter in registry.list_adapters():
        name = adapter.name
        is_running = name in processes and processes[name].poll() is None
        cfg = config.get(name, {})
        result.append({
            "name": name,
            "status": "RUNNING" if is_running else "STOPPED",
            "description": adapter.description,
            "server_id": cfg.get("server_id", "None"),
        })
    return result

@app.post("/api/adapters/{name}/start")
def start_adapter(name: str):
    config = load_config()
    if name not in config:
        raise HTTPException(status_code=404, detail="Adapter not found")
    start_adapter_internal(name, config[name])
    return {"status": "started"}

@app.post("/api/adapters/{name}/stop")
def stop_adapter(name: str):
    if name not in processes or processes[name].poll() is not None:
        return {"status": "already stopped"}
    
    proc = processes[name]
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    processes.pop(name, None)
    return {"status": "stopped"}

class ConnectRequest(BaseModel):
    proxy_url: str
    server_id: str
    password_code: str

@app.post("/api/connection")
async def connect_proxy(req: ConnectRequest):
    global proxy_client, connection_info
    
    if proxy_client is not None:
        await proxy_client.aclose()
        
    try:
        client = SecureProxyClient(
            proxy_url=req.proxy_url,
            server_id=req.server_id,
            password_code=req.password_code,
            client_id="central-server"
        )
        await client.ensure_handshake()
        proxy_client = client
        connection_info["proxy_url"] = req.proxy_url
        connection_info["server_id"] = req.server_id
        connection_info["status"] = "Connected"
        return {"status": "connected"}
    except Exception as e:
        connection_info["status"] = f"Error: {e}"
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/connection")
def get_connection():
    return connection_info

@app.post("/api/connection/disconnect")
async def disconnect_proxy():
    global proxy_client, connection_info
    if proxy_client is not None:
        await proxy_client.aclose()
        proxy_client = None
    connection_info["status"] = "Disconnected"
    connection_info["proxy_url"] = None
    connection_info["server_id"] = None
    return {"status": "disconnected"}

@app.post("/ingest")
async def ingest_message(payload: dict, background_tasks: BackgroundTasks):
    global proxy_client
    if proxy_client and connection_info["status"] == "Connected":
        # Forward async in background to avoid blocking
        async def send_msg():
            try:
                await proxy_client.send(payload)
            except Exception as e:
                print(f"Failed to forward message: {e}")
        background_tasks.add_task(send_msg)
    else:
        print("Received payload but proxy not connected:", payload)
    
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run("adapters.server:app", host="127.0.0.1", port=8000, reload=False)
