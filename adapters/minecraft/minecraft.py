"""
Minecraft chat log adapter.

Tails a Minecraft server/client log file, extracts chat messages, and POSTs
each one to the backend /ingest endpoint. Guarantees:

  - Only new lines are read (persisted byte offset -> survives restarts).
  - Each parsed chat message is sent at most once (persisted "last sent"
    marker, keyed by file offset, guards against duplicate sends if the
    process crashes mid-batch).

Log lines this adapter recognizes (from `Server thread/INFO`, ignoring the
`[CHAT]` render-thread echo which is a duplicate of the same message):

    [18:13:15] [Server thread/INFO]: [Not Secure] <ChillMathew> hello guys
    [18:13:15] [Server thread/INFO]: <ChillMathew> hello guys   (secure variant)

Usage:
    python minecraft_log_adapter.py --log /path/to/latest.log \
        --backend-url http://localhost:8000/ingest \
        --server-id my-survival-server
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("minecraft_adapter")

# Matches the server-side chat log line only (skips the render-thread [CHAT]
# echo, and skips join/leave/system messages). Handles both the
# "[Not Secure] <name> msg" and secure "<name> msg" forms.
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
    file_offset: int  # byte offset immediately after this line in the log


class OffsetStore:
    """Persists (byte_offset, last_sent_offset) so restarts don't reprocess
    or re-send lines."""

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
    """Reads new complete lines appended to a growing log file, starting
    from a persisted offset."""

    def __init__(self, log_path: Path, start_offset: int = 0):
        self.log_path = log_path
        self._offset = start_offset

    def read_new_lines(self) -> list[tuple[str, int]]:
        """Returns list of (line, offset_after_line). Only returns complete
        lines (ones ending in '\n'), so a partially-written line is left for
        the next poll."""
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
                    # incomplete line at EOF, wait for more data
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


import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from client import IngestClient



async def run(
    log_path: Path,
    backend_url: str | None,
    server_id: str,
    state_path: Path,
    poll_interval: float,
    max_retries: int,
    proxy_url: str | None = None,
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

                # Already sent this exact line in a prior run that crashed
                # before we persisted read_offset past it.
                if offset_after <= store.last_sent_offset:
                    continue

                msg = parse_chat_message(line, offset_after)
                if msg is None:
                    # not a chat line (join/leave/system/etc) — still advance
                    # read_offset, nothing to send.
                    store.save()
                    continue

                await _send_with_retry(client, msg, max_retries)
                store.last_sent_offset = offset_after
                store.save()

            await asyncio.sleep(poll_interval)
    finally:
        await client.aclose()


async def _send_with_retry(
    client: IngestClient, msg: ChatMessage, max_retries: int
) -> None:
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            payload = {
                "platform": "minecraft",
                "user_id": msg.username,
                "server_id": client.server_id,
                "message": msg.message,
            }
            await client.send(payload)
            log.info("Sent <%s> %s", msg.username, msg.message)
            return
        except httpx.HTTPStatusError as exc:
            # 4xx: backend rejected the payload; don't spin forever on a bad
            # message, log and move on so we don't block the whole stream.
            if 400 <= exc.response.status_code < 500:
                log.error(
                    "Backend rejected message from %s (status %d): %s",
                    msg.username,
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
    log.error(
        "Giving up on message from %s after %d attempts: %s",
        msg.username,
        max_retries,
        msg.message,
    )


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
        help="Where to persist read/send offsets (default: <log>.adapter-state.json)",
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
