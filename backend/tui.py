import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from services.proxy_agent import ProxyAgent, ProxyState, load_state, save_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent / "backend_state.json"


@dataclass
class AdapterConfig:
    name: str
    script: str
    description: str
    default_args: list[str] = field(default_factory=list)


class AdapterManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.processes: dict[str, subprocess.Popen] = {}


class BackendTUI:
    def __init__(self) -> None:
        load_state()
        self.state = ProxyState.current()
        self.proxy_agent: ProxyAgent | None = None
        self.proxy_url: str | None = None
        self.username: str | None = None
        self.password: str | None = None

    def run(self) -> None:
        print("TellMom Backend TUI")
        print("Type help for available commands")

        while True:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting")
                break

            if not raw:
                continue

            args = raw.split()
            command = args[0].lower()
            if command == "help":
                self.print_help()
            elif command == "status":
                self.print_status()
            elif command == "renew-passcode":
                self.renew_passcode()
            elif command == "set-proxy":
                self.set_proxy(args[1:])
            elif command == "register":
                asyncio.run(self.register())
            elif command == "login":
                asyncio.run(self.login())
            elif command == "connect":
                asyncio.run(self.connect())
            elif command == "exit":
                break
            else:
                print(f"Unknown command: {command}")

        save_state()

    def print_help(self) -> None:
        print("Available commands:")
        print("  help              Show this help")
        print("  status            Show current passcode and proxy state")
        print("  renew-passcode    Generate a new backend password code")
        print("  set-proxy URL USER PASS  Configure proxy connection")
        print("  register          Register this backend with the proxy")
        print("  login             Log in to the proxy using configured credentials")
        print("  connect           Open the websocket connection to the proxy")
        print("  exit              Quit")

    def print_status(self) -> None:
        print(f"Current password code: {self.state.password_code}")
        print(f"Proxy URL: {self.proxy_url or '(not configured)'}")
        print(f"Username: {self.username or '(not configured)'}")
        print(f"Connected: {self.proxy_agent is not None}")

    def renew_passcode(self) -> None:
        new_code = ProxyState.renew_password_code()
        print(f"Passcode renewed: {new_code}")

    def set_proxy(self, args: list[str]) -> None:
        if len(args) < 3:
            print("Usage: set-proxy URL USER PASS")
            return
        self.proxy_url, self.username, self.password = args[0], args[1], args[2]
        print("Proxy configured")

    async def register(self) -> None:
        if not self.proxy_url or not self.username or not self.password:
            print("Proxy URL, username, and password are required")
            return
        self.proxy_agent = ProxyAgent(self.proxy_url, self.username, self.password)
        try:
            await self.proxy_agent.register()
            print(f"Registered server_id={self.proxy_agent.server_id}")
        except Exception as exc:
            print(f"Registration failed: {exc}")

    async def login(self) -> None:
        if not self.proxy_url or not self.username or not self.password:
            print("Proxy URL, username, and password are required")
            return
        self.proxy_agent = ProxyAgent(self.proxy_url, self.username, self.password)
        try:
            await self.proxy_agent.login()
            print(f"Logged into proxy as server_id={self.proxy_agent.server_id}")
        except Exception as exc:
            print(f"Login failed: {exc}")

    async def connect(self) -> None:
        if self.proxy_agent is None:
            print("Register or login first")
            return

        try:
            await self.proxy_agent.connect()
            print("Connected websocket to proxy")
        except Exception as exc:
            print(f"Connection failed: {exc}")


if __name__ == "__main__":
    tui = BackendTUI()
    tui.run()
