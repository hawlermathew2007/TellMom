from backend.services.proxy_agent import ProxyAgent
import logging

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.agent = None
        self.status = "Disconnected"

    async def update_config(self, proxy_url: str, username: str, password: str, local_url: str):
        if self.agent:
            await self.agent.stop()

        if not proxy_url or not username or not password or not local_url:
            self.status = "Config Missing"
            self.agent = None
            return
        self.agent = ProxyAgent(proxy_url, username, password, local_url)
        self.status = "Configured"

        try:
            await self.login()
        except Exception as e:
            logger.error(f"Auto-login failed: {e}")
            self.status = "Login Failed"
            self.agent = None
            return

        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Auto-connect failed: {e}")
            self.status = "Connect Failed"

    async def register(self):
        if not self.agent:
            raise ValueError("Agent not configured")
        await self.agent.register()
        self.status = "Registered"

    async def login(self):
        if not self.agent:
            raise ValueError("Agent not configured")
        await self.agent.login()
        self.status = "Logged In"

    async def connect(self):
        if not self.agent:
            raise ValueError("Agent not configured")
        await self.agent.connect()
        self.status = "Connected"

proxy_manager = ProxyManager()
