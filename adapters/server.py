import subprocess
import yaml
import uvicorn
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request

from adapters.base import AdapterRegistry
from adapters.minecraft.minecraft import plugin as minecraft_plugin
from adapters.client import SecureProxyClient
from backend.schemas.ingest import IngestRequest

CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"
BASE_DIR = Path(__file__).resolve().parent

registry = AdapterRegistry()
registry.register(minecraft_plugin)


def load_config() -> Dict[str, dict]:
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


class ServerState:
    """Holds all mutable runtime state for the app, replacing module-level globals."""

    def __init__(self) -> None:
        self.processes: Dict[str, subprocess.Popen] = {}
        self.proxy_client: Optional[SecureProxyClient] = None
        self.connection_info: Dict[str, Optional[str]] = {
            "proxy_url": None,
            "server_id": None,
            "status": "Disconnected",
        }

    def start_adapter(self, name: str, cfg: dict):
        if name in self.processes and self.processes[name].poll() is None:
            return

        adapter = registry.get(name)
        if not adapter:
            return

        log_file_path = BASE_DIR / f"{name}_output.log"
        log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")

        # Overwrite backend_url to point to this server
        cfg["backend_url"] = "http://127.0.0.1:8000/ingest"
        cfg["proxy_url"] = ""  # Disable proxy client inside adapter

        proc = adapter.launch(BASE_DIR, cfg, log_file)
        self.processes[name] = proc

    def stop_adapter(self, name: str) -> bool:
        if name not in self.processes or self.processes[name].poll() is not None:
            return False

        proc = self.processes[name]
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        self.processes.pop(name, None)
        return True

    def is_running(self, name: str) -> bool:
        return name in self.processes and self.processes[name].poll() is None

    async def connect(self, proxy_url: str, server_id: str, password_code: str):
        if self.proxy_client is not None:
            await self.proxy_client.aclose()

        try:
            client = SecureProxyClient(
                proxy_url=proxy_url,
                server_id=server_id,
                password_code=password_code,
                client_id="central-server",
            )
            await client.ensure_handshake()
            self.proxy_client = client
            self.connection_info["proxy_url"] = proxy_url
            self.connection_info["server_id"] = server_id
            self.connection_info["status"] = "Connected"
        except Exception as e:
            self.connection_info["status"] = f"Error: {e}"
            raise

    async def disconnect(self):
        if self.proxy_client is not None:
            await self.proxy_client.aclose()
            self.proxy_client = None
        self.connection_info["status"] = "Disconnected"
        self.connection_info["proxy_url"] = None
        self.connection_info["server_id"] = None

    async def forward(self, payload: dict):
        if self.proxy_client and self.connection_info["status"] == "Connected":
            try:
                await self.proxy_client.send(payload)
            except Exception as e:
                print(f"Failed to forward message: {e}")
        else:
            print("Received payload but proxy not connected:", payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.server = ServerState()

    config = load_config()
    for name, cfg in config.items():
        if cfg.get("auto_start"):
            app.state.server.start_adapter(name, cfg)
    yield


app = FastAPI(lifespan=lifespan)


def get_state(request: Request) -> ServerState:
    return request.app.state.server


@app.get("/api/adapters")
def list_adapters(request: Request):
    state = get_state(request)
    config = load_config()
    result = []
    for adapter in registry.list_adapters():
        name = adapter.name
        cfg = config.get(name, {})
        result.append(
            {
                "name": name,
                "status": "RUNNING" if state.is_running(name) else "STOPPED",
                "description": adapter.description,
                "server_id": cfg.get("server_id", "None"),
            }
        )
    return result


@app.post("/api/adapters/{name}/start")
def start_adapter(name: str, request: Request):
    config = load_config()
    if name not in config:
        raise HTTPException(status_code=404, detail="Adapter not found")
    get_state(request).start_adapter(name, config[name])
    return {"status": "started"}


@app.post("/api/adapters/{name}/stop")
def stop_adapter(name: str, request: Request):
    stopped = get_state(request).stop_adapter(name)
    return {"status": "stopped" if stopped else "already stopped"}


class ConnectRequest(BaseModel):
    proxy_url: str
    server_id: str
    password_code: str


@app.post("/api/connection")
async def connect_proxy(req: ConnectRequest, request: Request):
    state = get_state(request)
    try:
        await state.connect(req.proxy_url, req.server_id, req.password_code)
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/connection")
def get_connection(request: Request):
    return get_state(request).connection_info


@app.post("/api/connection/disconnect")
async def disconnect_proxy(request: Request):
    await get_state(request).disconnect()
    return {"status": "disconnected"}


@app.post("/ingest")
async def ingest_message(
    payload: IngestRequest, request: Request, background_tasks: BackgroundTasks
):
    state = get_state(request)
    # Put into a background task which will then get executed by client
    background_tasks.add_task(state.forward, payload.model_dump())
    return {"status": "received"}


if __name__ == "__main__":
    uvicorn.run("adapters.server:app", host="127.0.0.1", port=8000, reload=False)
