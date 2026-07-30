"""
Discord chat log adapter.
"""

from __future__ import annotations

import argparse
import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

import discord
import httpx
from ..base import BaseAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
log = logging.getLogger("discord_adapter")


class DiscordAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(
            name="discord",
            display_name="Discord Bot",
            default_config={
                "bot_token": "",
                "local_ingest_url": "http://localhost:8000/ingest",
                "server_id": "my-discord-server",
                "auto_start": False,
            },
            description="Discord bot that forwards chat",
        )

    def launch(self, config: Dict[str, Any], log_file: Any) -> subprocess.Popen:
        args = [
            sys.executable,
            "-m",
            "adapters.discord.discord",
            "--bot-token",
            str(config.get("bot_token", "")),
            "--server-id",
            str(config.get("server_id", "my-discord-server")),
            "--local-ingest-url",
            str(config.get("local_ingest_url", "http://localhost:8000/ingest")),
        ]

        return subprocess.Popen(args, stdout=log_file, stderr=subprocess.STDOUT)


plugin = DiscordAdapter()


def run_bot(bot_token: str, local_ingest_url: str, default_server_id: str):
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        log.info(f"Logged in as Discord Bot: {client.user} (ID: {client.user.id})")
        log.info(f"Ingesting chats to TellMom API at: {local_ingest_url}")
        log.info("Ready and listening for messages...")

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user or message.author.bot:
            return

        if not message.content or not message.content.strip():
            return

        server_id = (
            str(message.guild.id) if message.guild else f"dm-{message.channel.id}"
        )

        payload = {
            "platform": "discord",
            "user_id": str(message.author.id),
            "server_id": server_id,
            "message": message.content.strip(),
        }

        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(local_ingest_url, json=payload)
                if response.status_code in (200, 204, 201):
                    log.info(
                        f"Successfully ingested message from {message.author} "
                        f"(ID: {payload['user_id']}) in server/channel {payload['server_id']}"
                    )
                else:
                    log.error(
                        f"Failed to ingest message. Status: {response.status_code}, "
                        f"Response: {response.text}"
                    )
        except Exception as exc:
            log.error(f"Error forwarding message: {exc}")

    client.run(bot_token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TellMom Discord Bot Adapter")
    parser.add_argument("--bot-token", required=True, help="Discord Bot Token")
    parser.add_argument(
        "--local-ingest-url", required=True, help="Full URL of the /ingest endpoint"
    )
    parser.add_argument(
        "--server-id", required=True, help="Default identifier for this server"
    )

    args = parser.parse_args()

    if not args.bot_token:
        log.error("Cannot start bot: bot_token is empty or missing.")
        sys.exit(1)

    run_bot(
        bot_token=args.bot_token,
        local_ingest_url=args.local_ingest_url,
        default_server_id=args.server_id,
    )


if __name__ == "__main__":
    main()
