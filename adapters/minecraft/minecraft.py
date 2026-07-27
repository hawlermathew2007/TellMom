from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
from adapters.base import BaseAdapter
from adapters.config import HOST, PORT


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


class LogTailer:
    def __init__(self, log_path: Path):
        self.log_path = log_path

        if log_path.exists():
            self._offset = log_path.stat().st_size
        else:
            self._offset = 0

    def read_new_lines(self) -> list[tuple[str, int]]:
        if not self.log_path.exists():
            return []

        size = self.log_path.stat().st_size
        if size < self._offset:
            # File was truncated or recreated.
            self._offset = 0

        lines = []

        with self.log_path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(self._offset)

            while True:
                raw = f.readline()
                if not raw:
                    break
                if not raw.endswith("\n"):
                    break

                self._offset = f.tell()
                lines.append((raw.rstrip("\n"), self._offset))

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


async def send_with_retry(
    client: httpx.AsyncClient, url: str, payload: dict, max_retries: int = 5
) -> None:
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return
        except httpx.HTTPStatusError as exc:
            if 400 <= exc.response.status_code < 500:
                log.error(
                    "Backend rejected message (status %d): %s",
                    exc.response.status_code,
                    exc.response.text,
                )
                return
            log.warning(
                "Server error sending message (attempt %d/%d): %s",
                attempt,
                max_retries,
                exc,
            )
        except httpx.HTTPError as exc:
            log.warning(
                "Network error sending message (attempt %d/%d): %s",
                attempt,
                max_retries,
                exc,
            )

        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30.0)
    log.error("Giving up on message after %d attempts", max_retries)


async def run(
    log_path: Path,
    local_ingest_url: str,
    server_id: str,
    poll_interval: float,
    max_retries: int,
) -> None:
    tailer = LogTailer(log_path)

    log.info(
        "Configuration: %s (server id), %s (backend url), %s (poll interval), %s (max retries)",
        server_id,
        local_ingest_url,
        poll_interval,
        max_retries,
    )
    log.info("Watching the log file at %s)", log_path)

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            new_lines = tailer.read_new_lines()

            for line, offset_after in new_lines:
                msg = parse_chat_message(line, offset_after)
                if msg is None:
                    continue

                payload = {
                    "platform": "minecraft",
                    "user_id": msg.username,
                    "server_id": server_id,
                    "message": msg.message,
                }

                await send_with_retry(client, local_ingest_url, payload, max_retries)
                log.info("Sent <%s> %s", msg.username, msg.message)

            await asyncio.sleep(poll_interval)


class MinecraftAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            name="minecraft",
            display_name="Minecraft Log Tailer",
            default_config={
                "log_path": "~/.minecraft/logs/latest.log",
                "local_ingest_url": f"http://{HOST}:{PORT}/ingest",
                "server_id": "my-survival-server",
                "poll_interval": 1.0,
                "max_retries": 5,
                "auto_start": False,
            },
            description="Tails a Minecraft log and forwards chat",
        )

    def launch(self, config: Dict[str, Any], log_file: Any) -> subprocess.Popen:
        args = [
            sys.executable,
            "-m",
            "adapters.minecraft.minecraft",
            "--log",
            str(config.get("log_path", "latest.log")),
            "--server-id",
            str(config.get("server_id", "my-survival-server")),
            "--poll-interval",
            str(config.get("poll_interval", 1.0)),
            "--max-retries",
            str(config.get("max_retries", 5)),
        ]

        local_ingest_url = config.get(
            "local_ingest_url", "http://localhost:8000/ingest"
        )
        args.extend(["--local-ingest-url", local_ingest_url])

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
        "--local-ingest-url",
        required=True,
        help="Full URL of the /ingest endpoint",
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

    asyncio.run(
        run(
            log_path=args.log,
            local_ingest_url=args.local_ingest_url,
            server_id=args.server_id,
            poll_interval=args.poll_interval,
            max_retries=args.max_retries,
        )
    )


if __name__ == "__main__":
    main()
