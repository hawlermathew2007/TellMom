from backend.services.proxy_agent import ProxyAgent
import logging

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        self.agent = None
        self.status = "Disconnected"

    def update_config(self, proxy_url: str, username: str, password: str, local_url: str):
        if not proxy_url or not username or not password or not local_url:
            self.status = "Config Missing"
            self.agent = None
            return
        self.agent = ProxyAgent(proxy_url, username, password, local_url)
        self.status = "Configured"

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
