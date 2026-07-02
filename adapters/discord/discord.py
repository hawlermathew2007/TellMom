import os
import logging
import httpx
import discord
from dotenv import load_dotenv

# Set up logging format and levels
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("tellmom.discord_bot")

# Load environment variables from .env file
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TELLMOM_API_URL = os.getenv("TELLMOM_API_URL", "http://localhost:8000/api/ingest")

if not DISCORD_BOT_TOKEN:
    logger.warning("DISCORD_BOT_TOKEN environment variable not set. Please set it in your .env file or environment.")

# Configure intents: We need default intents + message_content to inspect message text
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logger.info(f"Logged in as Discord Bot: {client.user} (ID: {client.user.id})")
    logger.info(f"Ingesting chats to TellMom API at: {TELLMOM_API_URL}")
    logger.info("Ready and listening for messages...")

@client.event
async def on_message(message: discord.Message):
    # Ignore messages sent by the bot itself
    if message.author == client.user:
        return

    # Ignore other bot messages
    if message.author.bot:
        return

    # Ignore empty messages (e.g. system messages, pins, or attachments-only without text)
    if not message.content or not message.content.strip():
        return

    # Determine server/guild ID
    # Use guild ID if message was sent in a server, or dm channel ID for direct messages
    server_id = str(message.guild.id) if message.guild else f"dm-{message.channel.id}"

    # Prepare payload according to IngestRequest schema
    payload = {
        "platform": "discord",
        "user_id": str(message.author.id),
        "server_id": server_id,
        "message": message.content.strip(),
    }

    logger.debug(f"Intercepted message from {message.author.id}: '{payload['message']}'")

    # Forward to TellMom API
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(TELLMOM_API_URL, json=payload)
            if response.status_code == 204:
                logger.info(
                    f"Successfully ingested message from {message.author} "
                    f"(ID: {payload['user_id']}) in server/channel {payload['server_id']}"
                )
            else:
                logger.error(
                    f"Failed to ingest message. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
    except httpx.RequestError as exc:
        logger.error(f"HTTP request error forwarding message to TellMom API: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected error forwarding message: {exc}")

if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        logger.error("Cannot start bot: DISCORD_BOT_TOKEN is missing.")
        exit(1)
    
    # Run the Discord bot client
    client.run(DISCORD_BOT_TOKEN)
