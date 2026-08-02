from __future__ import annotations

import asyncio
from typing import Any

from adapters.config import PROXY_URL, WS_URL
from shared.services.state_client import CommandError, StateStreamClient
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Log,
    Input,
    Button,
    Label,
    Checkbox,
    Static,
)
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual.screen import ModalScreen, Screen
from textual.reactive import reactive


class ConfirmModal(ModalScreen[bool]):
    """Small yes/no confirmation dialog."""

    CSS = """
    ConfirmModal {
        align: center middle;
    }
    #confirm_container {
        width: 50%;
        height: auto;
        background: $surface;
        border: solid $secondary;
        padding: 1 2;
    }
    #confirm_message {
        margin-bottom: 1;
    }
    """

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_container"):
            yield Label(self.message, id="confirm_message")
            with Horizontal():
                yield Button("Yes", id="confirm_yes", variant="error")
                yield Button("Cancel", id="confirm_no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm_yes")


class LogModal(ModalScreen[None]):
    """Shows an adapter's run log, with a manual refresh button."""

    CSS = """
    LogModal {
        align: center middle;
    }
    #log_container {
        width: 84%;
        height: 84%;
        background: $surface;
        border: solid $secondary;
        padding: 1;
    }
    #log_header {
        height: auto;
    }
    #adapter_log_widget {
        height: 1fr;
        border: solid $primary;
    }
    #log_buttons {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close"),
        Binding("r", "refresh_log", "Refresh"),
    ]

    def __init__(self, name: str, fetch_logs):
        super().__init__()
        self.adapter_name = name
        self.fetch_logs = fetch_logs  # async callable -> str

    def compose(self) -> ComposeResult:
        with Vertical(id="log_container"):
            with Horizontal(id="log_header"):
                yield Label(f"Logs for {self.adapter_name}")
            yield Log(id="adapter_log_widget")
            with Horizontal(id="log_buttons"):
                yield Button("Refresh", id="refresh_log_btn", variant="primary")
                yield Button("Close", id="close_log_btn", variant="error")

    async def on_mount(self) -> None:
        await self.action_refresh_log()

    async def action_refresh_log(self) -> None:
        log_widget = self.query_one("#adapter_log_widget", Log)
        log_widget.clear()
        logs = await self.fetch_logs(self.adapter_name)
        log_widget.write(logs or "(no log output yet)")

    def action_dismiss_modal(self) -> None:
        self.dismiss()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_log_btn":
            self.dismiss()
        elif event.button.id == "refresh_log_btn":
            await self.action_refresh_log()


class ConfigModal(ModalScreen[dict]):
    """Edit an adapter's configuration and save it back."""

    CSS = """
    ConfigModal {
        align: center middle;
    }
    #config_container {
        width: 60%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $secondary;
        padding: 1 2;
    }
    #config_scroll {
        height: 1fr;
        min-height: 5;
    }
    .config_input {
        margin-bottom: 1;
    }
    .config_label {
        margin-top: 1;
    }
    #config_buttons {
        margin-top: 1;
        height: auto;
        align: right middle;
    }
    #config_error {
        color: $error;
        margin-top: 1;
    }
    """

    def __init__(self, name: str, config: dict):
        super().__init__()
        self.adapter_name = name
        self.config_data = config
        self.inputs: dict[str, Input | Checkbox] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="config_container"):
            yield Label(f"Configure {self.adapter_name}", classes="header")

            # Scrollable container for dynamically generated inputs
            with VerticalScroll(id="config_scroll"):
                if not self.config_data:
                    yield Label("This adapter has no configurable options.")
                for key, val in self.config_data.items():
                    if isinstance(val, bool):
                        cb = Checkbox(key, value=val, id=f"cfg_{key}")
                        self.inputs[key] = cb
                        yield cb
                    else:
                        yield Label(key, classes="config_label")
                        inp = Input(
                            value=str(val),
                            placeholder=key,
                            id=f"cfg_{key}",
                            classes="config_input",
                        )
                        self.inputs[key] = inp
                        yield inp

            # Fixed footer elements (always visible)
            yield Label("", id="config_error")
            with Horizontal(id="config_buttons"):
                yield Button("Save", id="save_cfg_btn", variant="success")
                yield Button("Cancel", id="cancel_cfg_btn", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_cfg_btn":
            self.dismiss(None)
        elif event.button.id == "save_cfg_btn":
            new_config = {}
            error_label = self.query_one("#config_error", Label)
            for key, widget in self.inputs.items():
                if isinstance(widget, Checkbox):
                    new_config[key] = widget.value
                    continue
                orig_val = self.config_data.get(key, "")
                raw = widget.value
                try:
                    if isinstance(orig_val, int):
                        new_config[key] = int(raw)
                    elif isinstance(orig_val, float):
                        new_config[key] = float(raw)
                    else:
                        new_config[key] = raw
                except ValueError:
                    error_label.update(f"Invalid value for '{key}', expected a number.")
                    return
            error_label.update("")
            self.dismiss(new_config)


class TellMomTUI(App):
    CSS = """
    #main_container {
        layout: horizontal;
    }
    #left_panel {
        width: 68%;
        border: solid green;
    }
    #right_panel {
        width: 32%;
        border: solid blue;
        padding: 1;
    }
    DataTable {
        height: 1fr;
    }
    #adapter_controls {
        height: auto;
        padding: 1;
    }
    #selected_adapter_line {
        padding: 0 1;
        color: $text-muted;
    }
    Log {
        height: 10;
        border-top: solid green;
    }
    .input_row {
        margin-bottom: 1;
    }
    Button {
        margin-right: 1;
    }
    .section_header {
        margin-top: 1;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start_adapter", "Start"),
        Binding("x", "stop_adapter", "Stop"),
        Binding("r", "restart_adapter", "Restart"),
        Binding("c", "configure_adapter", "Configure"),
        Binding("l", "show_logs", "Logs"),
    ]

    connection_status: reactive[str] = reactive("Checking...")

    def __init__(self):
        super().__init__()
        self.client = StateStreamClient(
            WS_URL,
            on_snapshot=self.apply_snapshot,
            on_status=self.on_stream_status,
        )
        self.adapter_configs: dict[str, dict] = {}
        self.adapter_autostart: dict[str, bool] = {}
        self.initial_config_loaded: bool = False
        self.stream_online: bool | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main_container"):
            with Vertical(id="left_panel"):
                yield DataTable(id="adapters_table")
                yield Static("Selected: (none)", id="selected_adapter_line")
                with Horizontal(id="adapter_controls"):
                    yield Button("Start", id="btn_start_adapter", variant="success")
                    yield Button("Stop", id="btn_stop_adapter", variant="error")
                    yield Button("Restart", id="btn_restart_adapter", variant="warning")
                    yield Button(
                        "Configure", id="btn_configure_adapter", variant="primary"
                    )
                    yield Button("Show Logs", id="btn_show_logs")
                yield Log(id="logs_panel")
            with Vertical(id="right_panel"):
                yield Label("Connection to Remote Proxy", classes="section_header")
                yield Label("Status: Checking...", id="conn_status")
                yield Input(
                    value=PROXY_URL,
                    placeholder="Proxy URL",
                    id="input_proxy_url",
                    classes="input_row",
                )
                yield Input(
                    placeholder="Server ID", id="input_server_id", classes="input_row"
                )
                yield Input(
                    placeholder="Password Code",
                    id="input_password",
                    password=True,
                    classes="input_row",
                )
                with Horizontal():
                    yield Button("Connect", id="btn_connect", variant="success")
                    yield Button("Disconnect", id="btn_disconnect", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Status", "Autostart", "Description", "Server ID")
        self.stream_state()

    @work(exclusive=True)
    async def stream_state(self) -> None:
        """Hold the adapter websocket open; the server pushes what changed."""
        await self.client.run()

    @property
    def base_screen(self) -> Screen:
        """The main screen: pushed state keeps rendering while a modal is open."""
        return self.screen_stack[0]

    def get_selected_adapter(self) -> str | None:
        table = self.base_screen.query_one(DataTable)
        if table.row_count == 0:
            return None
        try:
            return str(table.get_row_at(table.cursor_coordinate.row)[0])
        except Exception:
            return None

    def log_line(self, message: str) -> None:
        self.base_screen.query_one("#logs_panel", Log).write_line(message)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        name = self.get_selected_adapter()
        self.base_screen.query_one("#selected_adapter_line", Static).update(
            f"Selected: {name}" if name else "Selected: (none)"
        )

    def apply_snapshot(self, data: dict[str, Any]) -> None:
        self.render_adapters(data.get("adapters") or [])
        self.render_connection(data.get("connection") or {})

    def render_adapters(self, adapters: list[dict]) -> None:
        table = self.base_screen.query_one(DataTable)
        cursor_row = table.cursor_coordinate.row
        table.clear()
        for adp in adapters:
            name = adp["name"]
            config = adp.get("config", {})
            self.adapter_configs[name] = config
            autostart = bool(config.get("auto_start", False))
            self.adapter_autostart[name] = autostart
            status = (
                f"[green]{adp['status']}[/]"
                if adp["status"] == "RUNNING"
                else f"[red]{adp['status']}[/]"
            )
            autostart_display = "[green]on[/]" if autostart else "[grey50]off[/]"
            table.add_row(
                name,
                status,
                autostart_display,
                adp["description"],
                adp["server_id"],
            )
        if table.row_count and cursor_row < table.row_count:
            table.move_cursor(row=cursor_row)

    def render_connection(self, conn: dict) -> None:
        status = conn.get("status", "Unknown")
        color = (
            "green" if status == "Connected" else "red" if "Error" in status else "yellow"
        )
        screen = self.base_screen
        screen.query_one("#conn_status", Label).update(f"Status: [{color}]{status}[/]")

        # Only on the first snapshot: later ones must not overwrite typing.
        if self.initial_config_loaded:
            return
        saved_config = conn.get("saved_config") or {}
        if saved_config:
            screen.query_one("#input_proxy_url", Input).value = saved_config.get(
                "proxy_url", PROXY_URL
            )
            screen.query_one("#input_server_id", Input).value = saved_config.get(
                "server_id", ""
            )
            screen.query_one("#input_password", Input).value = saved_config.get(
                "password_code", ""
            )
        self.initial_config_loaded = True

    def on_stream_status(self, connected: bool, message: str) -> None:
        if connected == self.stream_online:
            return
        self.stream_online = connected

        if connected:
            self.log_line("Connected to adapter service stream.")
            return

        self.base_screen.query_one("#conn_status", Label).update(
            "Status: [red]Adapter service offline[/]"
        )
        self.log_line(f"Adapter service stream offline ({message}). Retrying…")

    async def run_action_command(self, action: str, label: str, **params: Any) -> bool:
        """Send one command over the stream and report how it went."""
        try:
            await self.client.request(action, **params)
        except CommandError as e:
            self.log_line(f"{label} failed: {e}")
        except ConnectionError:
            self.log_line(f"{label} failed: adapter service is offline.")
        except asyncio.TimeoutError:
            self.log_line(f"{label} timed out.")
        except Exception as e:
            self.log_line(f"{label} failed: {e}")
        else:
            self.log_line(f"{label} ok.")
            return True
        return False

    async def action_start_adapter(self) -> None:
        name = self.get_selected_adapter()
        if not name:
            return
        await self.run_action_command("start_adapter", f"Start {name}", name=name)

    async def action_stop_adapter(self) -> None:
        name = self.get_selected_adapter()
        if not name:
            return
        await self.run_action_command("stop_adapter", f"Stop {name}", name=name)

    async def action_restart_adapter(self) -> None:
        name = self.get_selected_adapter()
        if not name:
            return
        await self.run_action_command("restart_adapter", f"Restart {name}", name=name)

    async def action_configure_adapter(self) -> None:
        name = self.get_selected_adapter()
        if not name:
            return
        config = self.adapter_configs.get(name, {})

        def check_result(new_config: dict | None):
            if new_config is not None:
                self.save_adapter_config(name, new_config)

        self.push_screen(ConfigModal(name, config), check_result)

    def save_adapter_config(self, name: str, new_config: dict) -> None:
        self.run_worker(
            self.run_action_command(
                "set_adapter_config",
                f"Save config for {name}",
                name=name,
                config=new_config,
            )
        )

    async def fetch_adapter_logs(self, name: str) -> str:
        try:
            result = await self.client.request("adapter_logs", name=name)
            return result.get("logs", "")
        except Exception as e:
            self.log_line(f"Error getting logs: {e}")
        return ""

    async def action_show_logs(self) -> None:
        name = self.get_selected_adapter()
        if not name:
            return
        self.push_screen(LogModal(name, self.fetch_adapter_logs))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn_start_adapter":
            await self.action_start_adapter()
        elif button_id == "btn_stop_adapter":
            await self.action_stop_adapter()
        elif button_id == "btn_restart_adapter":
            await self.action_restart_adapter()
        elif button_id == "btn_configure_adapter":
            await self.action_configure_adapter()
        elif button_id == "btn_show_logs":
            await self.action_show_logs()

        elif button_id == "btn_connect":
            await self._connect()
        elif button_id == "btn_disconnect":
            await self._disconnect()

    async def _connect(self) -> None:
        screen = self.base_screen
        proxy_url = screen.query_one("#input_proxy_url", Input).value
        server_id = screen.query_one("#input_server_id", Input).value
        password = screen.query_one("#input_password", Input).value

        if not proxy_url or not server_id or not password:
            self.log_line("Please fill all connection fields.")
            return

        self.log_line("Connecting...")
        await self.run_action_command(
            "connect",
            "Connect to proxy",
            proxy_url=proxy_url,
            server_id=server_id,
            password_code=password,
        )

    async def _disconnect(self) -> None:
        await self.run_action_command("disconnect", "Disconnect from proxy")

    async def on_unmount(self) -> None:
        await self.client.aclose()


if __name__ == "__main__":
    app = TellMomTUI()
    app.run()
