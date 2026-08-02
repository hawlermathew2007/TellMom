import logging
import subprocess
import asyncio
import yaml
import uvicorn
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket

from adapters.base import AdapterRegistry
from adapters.minecraft.minecraft import plugin as minecraft_plugin
from adapters.discord.discord import plugin as discord_plugin
from adapters.client import SecureProxyClient
from backend.schemas.ingest import IngestRequest
from adapters.config import CONFIG_FILE, BASE_DIR, HOST, PORT, RECONNECT_INTERVAL
from shared.services.state_hub import StateHub, serve_state_stream


logger = logging.getLogger(__name__)

# How often adapter subprocesses are re-checked for liveness. Local only: a
# change here is broadcast, an unchanged snapshot costs nothing on the wire.
WATCH_INTERVAL = 1.0

LOG_TAIL_LINES = 100

# Registering all the different modules
registry = AdapterRegistry()
registry.register(minecraft_plugin)
registry.register(discord_plugin)


def read_raw_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def write_raw_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(cfg, f)


def load_config() -> Dict[str, dict]:
    cfg = {}
    for adapter in registry.list_adapters():
        cfg[adapter.name] = adapter.default_config.copy()

    user_cfg = read_raw_config()
    for name, default_val in cfg.items():
        if name in user_cfg:
            default_val.update(user_cfg[name])
    return cfg


def load_server_config() -> dict:
    return read_raw_config().get("server_config", {})


def save_server_config(proxy_url: str, server_id: str, password_code: str) -> dict:
    user_cfg = read_raw_config()
    server_config = {
        "proxy_url": proxy_url,
        "server_id": server_id,
        "password_code": password_code,
    }
    user_cfg["server_config"] = server_config
    write_raw_config(user_cfg)
    return server_config


def read_adapter_logs(name: str) -> str:
    log_file_path = BASE_DIR / "logs" / f"{name}_output.log"
    if not log_file_path.exists():
        return "No logs found."
    try:
        with open(log_file_path, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-LOG_TAIL_LINES:])
    except Exception as e:
        return f"Error reading logs: {e}"


class ServerState:
    """Holds all mutable runtime state for the app, replacing module-level globals."""

    def __init__(self, local_ingest_url: str) -> None:
        self.local_ingest_url = local_ingest_url
        self.processes: Dict[str, subprocess.Popen] = {}
        self.proxy_client: Optional[SecureProxyClient] = None
        self.connection_info: Dict[str, Optional[str]] = {
            "proxy_url": None,
            "server_id": None,
            "status": "Disconnected",
        }
        # Kept in memory so building a snapshot never touches the disk.
        self.config: Dict[str, dict] = load_config()
        self.saved_config: dict = load_server_config()
        self.hub = StateHub(self.snapshot, poll_interval=WATCH_INTERVAL)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "adapters": self.adapter_list(),
            "connection": {**self.connection_info, "saved_config": self.saved_config},
        }

    def adapter_list(self) -> List[dict]:
        result = []
        for adapter in registry.list_adapters():
            cfg = self.config.get(adapter.name, adapter.default_config.copy())
            result.append(
                {
                    "name": adapter.name,
                    "status": "RUNNING" if self.is_running(adapter.name) else "STOPPED",
                    "description": adapter.description,
                    "server_id": cfg.get("server_id", "None"),
                    "config": cfg,
                }
            )
        return result

    def start_adapter(self, name: str) -> None:
        adapter = registry.get(name)
        if adapter is None:
            raise LookupError(f"Adapter not found: {name}")

        if self.is_running(name):
            return

        config = self.config.get(name, adapter.default_config.copy())
        log_file_path = BASE_DIR / "logs" / f"{name}_output.log"
        log_file_path.parent.mkdir(exist_ok=True, parents=True)
        log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")
        launch_config = {
            **config,
            "local_ingest_url": f"{self.local_ingest_url}/ingest",
        }
        self.processes[name] = adapter.launch(launch_config, log_file)

    def stop_adapter(self, name: str) -> bool:
        if not self.is_running(name):
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

    def update_adapter_config(self, name: str, new_config: dict) -> None:
        if registry.get(name) is None:
            raise LookupError(f"Adapter not found: {name}")

        self.config.setdefault(name, {}).update(new_config)
        raw = read_raw_config()
        raw[name] = self.config[name]
        write_raw_config(raw)

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
                logger.error(f"Failed to forward message: {e}")
                logger.error(f"Error message payload: {payload}")
        else:
            logger.error("Received payload but proxy not connected:", payload)


async def run_command(state: ServerState, action: str, params: dict) -> dict:
    """Every mutating operation, reachable from the websocket and from HTTP."""
    name = str(params.get("name", ""))

    if action == "start_adapter":
        state.start_adapter(name)
        return {"status": "started"}

    if action == "stop_adapter":
        return {"status": "stopped" if state.stop_adapter(name) else "already stopped"}

    if action == "restart_adapter":
        state.stop_adapter(name)
        state.start_adapter(name)
        return {"status": "restarted"}

    if action == "set_adapter_config":
        state.update_adapter_config(name, params.get("config") or {})
        return {"status": "success"}

    if action == "adapter_logs":
        return {"logs": read_adapter_logs(name)}

    if action == "connect":
        request = ConnectRequest.model_validate(params)
        await state.connect(request.proxy_url, request.server_id, request.password_code)
        state.saved_config = save_server_config(
            request.proxy_url, request.server_id, request.password_code
        )
        return {"status": "connected"}

    if action == "disconnect":
        await state.disconnect()
        return {"status": "disconnected"}

    raise ValueError(f"Unknown adapter action: {action}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    URL = f"http://{HOST}:{PORT}"
    app.state.server = ServerState(URL)

    async def reconnect_loop():
        while True:
            try:
                if (
                    app.state.server.connection_info.get("status", "").lower()
                    != "connected"
                ):
                    server_config = app.state.server.saved_config
                    proxy_url = server_config.get("proxy_url")
                    server_id = server_config.get("server_id")
                    password_code = server_config.get("password_code")

                    if proxy_url and server_id and password_code:
                        try:
                            await app.state.server.connect(
                                proxy_url,
                                server_id,
                                password_code,
                            )
                        except Exception as e:
                            logger.error(f"Failed to auto-connect to proxy: {e}")

                await asyncio.sleep(RECONNECT_INTERVAL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconnect loop error: {e}")
                await asyncio.sleep(RECONNECT_INTERVAL)

    for name, cfg in app.state.server.config.items():
        if cfg.get("auto_start"):
            app.state.server.start_adapter(name)

    tasks = [
        asyncio.create_task(reconnect_loop()),
        # Adapter processes die and proxy links drop on their own; the watcher
        # turns that into a push instead of clients asking every few seconds.
        asyncio.create_task(app.state.server.hub.run_watcher()),
    ]

    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan)


def get_state(request: Request) -> ServerState:
    return request.app.state.server


async def http_command(request: Request, action: str, params: dict) -> dict:
    state = get_state(request)
    try:
        result = await run_command(state, action, params)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    await state.hub.publish()
    return result


@app.websocket("/api/ws")
async def api_stream(websocket: WebSocket) -> None:
    """Live adapter/connection state, and the channel their actions run on."""
    state: ServerState = websocket.app.state.server

    def handle(action: str, params: dict):
        return run_command(state, action, params)

    await serve_state_stream(state.hub, websocket, handle)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class AdapterConfig(BaseModel):
    config: dict


@app.post("/api/adapters/{name}/config")
async def update_adapter_config(name: str, payload: AdapterConfig, request: Request):
    return await http_command(
        request, "set_adapter_config", {"name": name, "config": payload.config}
    )


@app.get("/api/adapters/{name}/logs")
def get_adapter_logs(name: str):
    return {"logs": read_adapter_logs(name)}


@app.post("/api/adapters/{name}/start")
async def start_adapter(name: str, request: Request):
    return await http_command(request, "start_adapter", {"name": name})


@app.post("/api/adapters/{name}/stop")
async def stop_adapter(name: str, request: Request):
    return await http_command(request, "stop_adapter", {"name": name})


class ConnectRequest(BaseModel):
    proxy_url: str
    server_id: str
    password_code: str


@app.post("/api/connection")
async def connect_proxy(req: ConnectRequest, request: Request):
    return await http_command(request, "connect", req.model_dump())


@app.post("/api/connection/disconnect")
async def disconnect_proxy(request: Request):
    return await http_command(request, "disconnect", {})


@app.post("/ingest")
async def ingest_message(
    payload: IngestRequest, request: Request, background_tasks: BackgroundTasks
):
    state = get_state(request)
    # Put into a background task which will then get executed by client
    background_tasks.add_task(state.forward, payload.model_dump())
    return {"status": "received"}


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("adapters.main:app", host=HOST, port=PORT, reload=args.reload)
