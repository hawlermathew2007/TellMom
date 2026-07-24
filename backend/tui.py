from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Any

import httpx
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, Label, Log, Static

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8000/management"
DEFAULT_LOCAL_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 10.0


@dataclass
class ConfigState:
    proxy_url: str = ""
    username: str = ""
    password: str = ""
    local_url: str = DEFAULT_LOCAL_URL

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "ConfigState":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def as_payload(self) -> dict[str, str]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def is_complete(self) -> bool:
        return all(self.as_payload().values())


class BackendTUI(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #main-grid {
        layout: grid;
        grid-size: 2 2;
        grid-rows: auto 1fr;
        grid-columns: 1fr 1fr;
        grid-gutter: 1 2;
        margin: 1 2;
        height: 100%;
    }

    .panel {
        border: round $primary;
        padding: 1 2;
        background: $panel;
        height: auto;
    }

    .panel-title {
        text-align: left;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
        width: 100%;
        border-bottom: solid $primary-darken-1;
        padding-bottom: 1;
    }

    .row {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }

    .input-label {
        width: 12;
        content-align: right middle;
        padding-right: 1;
        color: $text-muted;
    }

    Input {
        width: 1fr;
    }

    #actions-panel {
        height: auto;
    }

    .btn-row {
        height: auto;
        layout: horizontal;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
        min-width: 12;
    }

    Button.copy-btn {
        min-width: 6;
        width: auto;
        margin: 0 0 0 1;
    }

    #status-panel {
        row-span: 2;
        height: 100%;
    }

    .status-card {
        border: round $accent;
        padding: 1;
        margin-bottom: 1;
        height: auto;
        background: $surface-darken-1;
    }

    .status-card-label {
        color: $text-muted;
        text-style: italic;
    }

    .status-value-row {
        layout: horizontal;
        align: left middle;
        height: 3;
    }

    .status-value {
        width: 1fr;
        text-style: bold;
        content-align: left middle;
    }

    .status-pill-online {
        color: $success;
    }

    .status-pill-offline {
        color: $error;
    }

    .status-pill-unknown {
        color: $warning;
    }

    #log-view {
        border: solid $accent;
        height: 1fr;
        margin-top: 1;
        background: $surface-darken-3;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    status_text: reactive[str] = reactive("Unknown")
    server_id: reactive[str] = reactive("")
    passcode: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Grid(id="main-grid"):
            with Container(classes="panel", id="config-panel"):
                yield from self._config_widgets()
            with Container(classes="panel", id="status-panel"):
                yield from self._status_widgets()
            with Container(classes="panel", id="actions-panel"):
                yield from self._action_widgets()

        yield Footer()

    @staticmethod
    def _config_widgets() -> ComposeResult:
        yield Label("⚙️  Configuration", classes="panel-title")
        with Horizontal(classes="row"):
            yield Label("Proxy URL", classes="input-label")
            yield Input(placeholder="http://example.com", id="input-proxy-url")
        with Horizontal(classes="row"):
            yield Label("Username", classes="input-label")
            yield Input(placeholder="Username", id="input-username")
        with Horizontal(classes="row"):
            yield Label("Password", classes="input-label")
            yield Input(placeholder="Password", password=True, id="input-password")
        with Horizontal(classes="row"):
            yield Label("Local URL", classes="input-label")
            yield Input(
                value=DEFAULT_LOCAL_URL,
                placeholder=DEFAULT_LOCAL_URL,
                id="input-local-url",
            )
        with Horizontal(classes="btn-row"):
            yield Button("💾 Save & Apply", id="btn-set-config", variant="primary")

    @staticmethod
    def _status_widgets() -> ComposeResult:
        yield Label("📊 Status", classes="panel-title")

        with Container(classes="status-card"):
            yield Static("Connection", classes="status-card-label")
            yield Static(
                "Unknown",
                id="status-display",
                classes="status-value status-pill-unknown",
            )

        with Container(classes="status-card"):
            yield Static("Server ID", classes="status-card-label")
            with Horizontal(classes="status-value-row"):
                yield Static("—", id="serverid-display", classes="status-value")
                yield Button(
                    "📋", id="btn-copy-serverid", classes="copy-btn", disabled=True
                )

        with Container(classes="status-card"):
            yield Static("Passcode", classes="status-card-label")
            with Horizontal(classes="status-value-row"):
                yield Static("—", id="passcode-display", classes="status-value")
                yield Button(
                    "📋", id="btn-copy-passcode", classes="copy-btn", disabled=True
                )

        yield Log(id="log-view")

    @staticmethod
    def _action_widgets() -> ComposeResult:
        yield Label("🚀 Proxy Actions", classes="panel-title")
        with Horizontal(classes="btn-row"):
            yield Button("Register", id="btn-register")
            yield Button("Login", id="btn-login")
            yield Button("Connect WS", id="btn-connect", variant="success")
        with Horizontal(classes="btn-row"):
            yield Button(
                "🔄 Renew Passcode", id="btn-renew-passcode", variant="warning"
            )

    def on_mount(self) -> None:
        self.fetch_state_and_status()
        self.set_interval(5.0, self.fetch_status_only)

    def watch_status_text(self, status: str) -> None:
        widget = self.query_one("#status-display", Static)
        widget.update(status)
        widget.set_classes(f"status-value {self._status_pill_class(status)}")

    def watch_server_id(self, value: str) -> None:
        self.query_one("#serverid-display", Static).update(value or "—")
        self.query_one("#btn-copy-serverid", Button).disabled = not bool(value)

    def watch_passcode(self, value: str) -> None:
        self.query_one("#passcode-display", Static).update(value or "—")
        self.query_one("#btn-copy-passcode", Button).disabled = not bool(value)

    @staticmethod
    def _status_pill_class(status: str) -> str:
        lowered = status.lower()
        if "offline" in lowered or "error" in lowered:
            return "status-pill-offline"
        if "online" in lowered or "connected" in lowered:
            return "status-pill-online"
        return "status-pill-unknown"

    def log_message(self, message: str) -> None:
        self.query_one("#log-view", Log).write_line(message)

    def copy_value_to_clipboard(self, label: str, value: str) -> None:
        """Copy `value` to the system clipboard, with UX feedback."""
        if not value:
            self.log_message(f"Nothing to copy for {label}.")
            return
        try:
            # Try pyperclip first
            try:
                import pyperclip
                pyperclip.copy(value)
            except ImportError:
                # Fallback to subprocess for linux/mac
                import subprocess
                import sys
                import shutil
                if sys.platform == "linux":
                    if shutil.which("xclip"):
                        subprocess.run(["xclip", "-selection", "clipboard"], input=value.encode("utf-8"), check=True)
                    elif shutil.which("wl-copy"):
                        subprocess.run(["wl-copy"], input=value.encode("utf-8"), check=True)
                    elif shutil.which("xsel"):
                        subprocess.run(["xsel", "--clipboard", "--input"], input=value.encode("utf-8"), check=True)
                    else:
                        self.copy_to_clipboard(value)
                elif sys.platform == "darwin":
                    subprocess.run(["pbcopy"], input=value.encode("utf-8"), check=True)
                else:
                    self.copy_to_clipboard(value)

            self.log_message(f"Copied {label} to clipboard.")
            self.notify(
                f"{label} copied to clipboard", severity="information", timeout=2
            )
        except Exception as e:
            self.log_message(f"Clipboard error for {label}: {e}")
            self.notify(f"Could not copy {label}", severity="error", timeout=3)

    def _config_from_inputs(self) -> ConfigState:
        return ConfigState(
            proxy_url=self.query_one("#input-proxy-url", Input).value,
            username=self.query_one("#input-username", Input).value,
            password=self.query_one("#input-password", Input).value,
            local_url=self.query_one("#input-local-url", Input).value,
        )

    def _apply_config_to_inputs(self, config: ConfigState) -> None:
        self.query_one("#input-proxy-url", Input).value = config.proxy_url
        self.query_one("#input-username", Input).value = config.username
        self.query_one("#input-password", Input).value = config.password
        self.query_one("#input-local-url", Input).value = (
            config.local_url or DEFAULT_LOCAL_URL
        )

    @work(exclusive=True)
    async def fetch_state_and_status(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                res = await client.get(f"{API_BASE}/state")
                if res.status_code == 200:
                    data = res.json()
                    self.passcode = data.get("password_code", "")
                    self._apply_config_to_inputs(ConfigState.from_api(data))
                await self.fetch_status_only()
        except httpx.ConnectError:
            self.status_text = "Backend Offline"
            self.log_message(
                "Could not connect to backend. Is the FastAPI service running on port 8000?"
            )
        except Exception as e:
            self.log_message(f"Error fetching state: {e}")

    @work(exclusive=True)
    async def fetch_status_only(self) -> None:
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                res = await client.get(f"{API_BASE}/status")
                if res.status_code == 200:
                    data = res.json()
                    self.status_text = data.get("status", "Unknown")
                    self.server_id = data.get("server_id", "")
        except httpx.ConnectError:
            self.status_text = "Backend Offline"
        except Exception:
            pass

    @work(exclusive=True)
    async def do_api_call(
        self,
        method: str,
        endpoint: str,
        start_msg: str,
        success_msg: str,
        json_data: dict | None = None,
    ) -> None:
        self.log_message(start_msg)
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                if method == "POST":
                    res = await client.post(f"{API_BASE}{endpoint}", json=json_data)
                elif method == "GET":
                    res = await client.get(f"{API_BASE}{endpoint}")
                else:
                    self.log_message(f"Unsupported method: {method}")
                    return

                if res.status_code != 200:
                    self.log_message(f"Error ({res.status_code}): {res.text}")
                    return

                self.log_message(success_msg)
                if endpoint == "/renew_passcode":
                    self.passcode = res.json().get("passcode", self.passcode)

                await self.fetch_status_only()
        except httpx.ConnectError:
            self.log_message("Connection error: backend is offline.")
        except Exception as e:
            self.log_message(f"Exception: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        handler = self._BUTTON_HANDLERS.get(event.button.id)
        if handler:
            await handler(self)

    async def _handle_renew_passcode(self) -> None:
        self.do_api_call(
            "POST", "/renew_passcode", "Renewing passcode…", "Passcode renewed."
        )

    async def _handle_set_config(self) -> None:
        config = self._config_from_inputs()
        if not config.is_complete():
            self.log_message("All configuration fields are required.")
            self.notify("Fill in every field before saving.", severity="warning")
            return
        self.do_api_call(
            "POST",
            "/state",
            "Saving configuration…",
            "Configuration saved.",
            config.as_payload(),
        )

    async def _handle_register(self) -> None:
        self.do_api_call(
            "POST", "/register", "Registering on proxy…", "Registration complete."
        )

    async def _handle_login(self) -> None:
        self.do_api_call("POST", "/login", "Logging in…", "Login complete.")

    async def _handle_connect(self) -> None:
        self.do_api_call(
            "POST", "/connect", "Connecting to proxy websocket…", "Connected."
        )

    async def _handle_copy_server_id(self) -> None:
        self.copy_value_to_clipboard("Server ID", self.server_id)

    async def _handle_copy_passcode(self) -> None:
        self.copy_value_to_clipboard("Passcode", self.passcode)

    _BUTTON_HANDLERS = {
        "btn-renew-passcode": _handle_renew_passcode,
        "btn-set-config": _handle_set_config,
        "btn-register": _handle_register,
        "btn-login": _handle_login,
        "btn-connect": _handle_connect,
        "btn-copy-serverid": _handle_copy_server_id,
        "btn-copy-passcode": _handle_copy_passcode,
    }


if __name__ == "__main__":
    BackendTUI().run()
