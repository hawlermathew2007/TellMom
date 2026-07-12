from pathlib import Path
import subprocess
import sys
from typing import Dict, Any
from .base import AdapterPlugin

def launch_minecraft(base_dir: Path, cfg: Dict[str, Any], log_file: Any) -> subprocess.Popen:
    script_path = base_dir / "minecraft" / "minecraft.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--log",
        cfg["log_path"],
        "--server-id",
        cfg["server_id"]
    ]
    if cfg.get("backend_url"):
        cmd.extend(["--backend-url", cfg["backend_url"]])
    if cfg.get("proxy_url"):
        cmd.extend(["--proxy-url", cfg["proxy_url"]])
    if cfg.get("password_code"):
        cmd.extend(["--password-code", cfg["password_code"]])
    if cfg.get("poll_interval"):
        cmd.extend(["--poll-interval", str(cfg["poll_interval"])])
    if cfg.get("max_retries"):
        cmd.extend(["--max-retries", str(cfg["max_retries"])])
    return subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(base_dir),
    )

plugin = AdapterPlugin(
    name="minecraft",
    display_name="Minecraft Adapter",
    description="Tails Minecraft server/client logs and ingests chat messages.",
    default_config={
        "log_path": "minecraft/latest.log",
        "backend_url": "http://localhost:8000/api/ingest",
        "proxy_url": "",
        "password_code": "",
        "server_id": "minecraft-server-1",
        "poll_interval": "1.0",
        "max_retries": "5",
    },
    launch_fn=launch_minecraft,
)
