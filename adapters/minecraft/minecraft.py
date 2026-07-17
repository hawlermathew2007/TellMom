"""
Minecraft chat log adapter.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from adapters.base import BaseAdapter
from adapters.client import IngestClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("minecraft_adapter")


CHAT_LINE_RE = re.compile(
    r"""^\[\d{2}:\d{2}:\d{2}\]\s+
        \[Server\ thread/INFO\]:\s+
        (?:\[Not\ Secure\]\s+)?
        <(?P<username>[^>]+)>\s+
        (?P<message>.*)$
    """,
    re.VERBOSE,
)


@dataclass
class ChatMessage:
    username: str
    message: str
    file_offset: int


class OffsetStore:
    def __init__(self, path: Path):
        self.path = path
        self.read_offset: int = 0
        self.last_sent_offset: int = 0
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self.read_offset = data.get("read_offset", 0)
                self.last_sent_offset = data.get("last_sent_offset", 0)
            except (json.JSONDecodeError, OSError):
                log.warning("Could not read state file %s, starting fresh", self.path)

    def save(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "read_offset": self.read_offset,
                    "last_sent_offset": self.last_sent_offset,
                }
            )
        )


class LogTailer:
    def __init__(self, log_path: Path, start_offset: int = 0):
        self.log_path = log_path
        self._offset = start_offset

    def read_new_lines(self) -> list[tuple[str, int]]:
        if not self.log_path.exists():
            return []

        lines: list[tuple[str, int]] = []
        with self.log_path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(self._offset)
            while True:
                raw = f.readline()
                if not raw:
                    break
                if not raw.endswith("\n"):
                    break
                pos_after = f.tell()
                lines.append((raw.rstrip("\n"), pos_after))
                self._offset = pos_after
        return lines


def parse_chat_message(line: str, offset: int) -> Optional[ChatMessage]:
    m = CHAT_LINE_RE.match(line)
    if not m:
        return None
    return ChatMessage(
        username=m.group("username"),
        message=m.group("message"),
        file_offset=offset,
    )


async def run(
    log_path: Path,
    backend_url: str | None,
    server_id: str,
    state_path: Path,
    poll_interval: float,
    max_retries: int,
    proxy_url: str,
    password_code: str | None = None,
) -> None:
    store = OffsetStore(state_path)
    tailer = LogTailer(log_path, start_offset=store.read_offset)
    client = IngestClient(
        backend_url or "",
        server_id,
        proxy_url=proxy_url,
        password_code=password_code,
        client_id="minecraft-client",
    )

    log.info("Watching %s (starting at offset %d)", log_path, store.read_offset)

    try:
        while True:
            new_lines = tailer.read_new_lines()

            for line, offset_after in new_lines:
                store.read_offset = offset_after

                if offset_after <= store.last_sent_offset:
                    continue

                msg = parse_chat_message(line, offset_after)
                if msg is None:
                    store.save()
                    continue

                payload = {
                    "platform": "minecraft",
                    "user_id": msg.username,
                    "server_id": client.server_id,
                    "message": msg.message,
                }
                
                await client.send_with_retry(payload, max_retries)
                log.info("Sent <%s> %s", msg.username, msg.message)
                
                store.last_sent_offset = offset_after
                store.save()

            await asyncio.sleep(poll_interval)
    finally:
        await client.aclose()


class MinecraftAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            name="minecraft",
            display_name="Minecraft Log Tailer",
            default_config={
                "log_path": "latest.log",
                "backend_url": "http://localhost:8000/ingest",
                "proxy_url": "",
                "password_code": "",
                "server_id": "my-survival-server",
                "poll_interval": 1.0,
                "max_retries": 5
            },
            description="Tails a Minecraft log and forwards chat"
        )
        
    def launch(self, base_dir: Path, config: Dict[str, Any], log_file: Any) -> subprocess.Popen:
        args = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--log", str(config.get("log_path", "latest.log")),
            "--server-id", str(config.get("server_id", "my-survival-server")),
            "--poll-interval", str(config.get("poll_interval", 1.0)),
            "--max-retries", str(config.get("max_retries", 5))
        ]
        
        backend_url = config.get("backend_url", "")
        if backend_url:
            args.extend(["--backend-url", backend_url])
            
        proxy_url = config.get("proxy_url", "")
        if proxy_url:
            args.extend(["--proxy-url", proxy_url])
            
        password_code = config.get("password_code", "")
        if password_code:
            args.extend(["--password-code", password_code])
            
        return subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT)

plugin = MinecraftAdapter()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tail a Minecraft log and forward chat to backend /ingest"
    )
    parser.add_argument(
        "--log",
        required=True,
        type=Path,
        help="Path to the Minecraft log file (e.g. latest.log)",
    )
    parser.add_argument(
        "--backend-url",
        required=False,
        default=None,
        help="Full URL of the /ingest endpoint when not using a proxy",
    )
    parser.add_argument(
        "--proxy-url",
        required=False,
        default=None,
        help="Full URL of the proxy server when using secure transport",
    )
    parser.add_argument(
        "--password-code",
        required=False,
        default=None,
        help="Passcode for client authentication to the local server via proxy",
    )
    parser.add_argument(
        "--server-id", required=True, help="Identifier for this Minecraft server"
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=None,
        help="Where to persist read/send offsets",
    )
    parser.add_argument(
        "--poll-interval", type=float, default=1.0, help="Seconds between log polls"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Retries per message on transient failure",
    )
    args = parser.parse_args()

    state_path = args.state_file or args.log.with_suffix(
        args.log.suffix + ".adapter-state.json"
    )

    if args.backend_url is None and args.proxy_url is None:
        raise SystemExit("Please provide either --backend-url or --proxy-url")

    asyncio.run(
        run(
            log_path=args.log,
            backend_url=args.backend_url,
            server_id=args.server_id,
            state_path=state_path,
            poll_interval=args.poll_interval,
            max_retries=args.max_retries,
            proxy_url=args.proxy_url,
            password_code=args.password_code,
        )
    )

if __name__ == "__main__":
    main()
