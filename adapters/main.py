import httpx
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Log, Input, Button, Label
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

API_URL = "http://127.0.0.1:8000/api"

class TellMomTUI(App):
    CSS = """
    #main_container {
        layout: horizontal;
    }
    #left_panel {
        width: 65%;
        border: solid green;
    }
    #right_panel {
        width: 35%;
        border: solid blue;
        padding: 1;
    }
    DataTable {
        height: 1fr;
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
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start_adapter", "Start Adapter"),
        Binding("x", "stop_adapter", "Stop Adapter"),
    ]

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=5.0)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main_container"):
            with Vertical(id="left_panel"):
                yield DataTable(id="adapters_table")
                yield Log(id="logs_panel")
            with Vertical(id="right_panel"):
                yield Label("Connection to Remote Proxy", classes="header")
                yield Label("Status: Checking...", id="conn_status")
                yield Input(placeholder="Proxy URL", id="input_proxy_url", classes="input_row")
                yield Input(placeholder="Server ID", id="input_server_id", classes="input_row")
                yield Input(placeholder="Password Code", id="input_password", password=True, classes="input_row")
                with Horizontal():
                    yield Button("Connect", id="btn_connect", variant="success")
                    yield Button("Disconnect", id="btn_disconnect", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Status", "Description", "Server ID")
        self.update_data()
        self.set_interval(2.0, self.update_data)

    async def update_data(self) -> None:
        try:
            # Update adapters
            resp = await self.client.get(f"{API_URL}/adapters")
            if resp.status_code == 200:
                adapters = resp.json()
                table = self.query_one(DataTable)
                row = table.cursor_coordinate.row
                table.clear()
                for adp in adapters:
                    status = f"[green]{adp['status']}[/]" if adp["status"] == "RUNNING" else f"[red]{adp['status']}[/]"
                    table.add_row(adp["name"], status, adp["description"], adp["server_id"])
                if row < table.row_count:
                    table.move_cursor(row=row)
            
            # Update connection status
            resp = await self.client.get(f"{API_URL}/connection")
            if resp.status_code == 200:
                conn = resp.json()
                status_label = self.query_one("#conn_status", Label)
                color = "green" if conn["status"] == "Connected" else "red" if "Error" in conn["status"] else "yellow"
                status_label.update(f"Status: [{color}]{conn['status']}[/]")
                
        except Exception as e:
            self.query_one(Log).write_line(f"Error fetching data: {e}")

    async def action_start_adapter(self) -> None:
        table = self.query_one(DataTable)
        log_panel = self.query_one(Log)
        
        if table.row_count == 0:
            return
        try:
            name = table.get_row_at(table.cursor_coordinate.row)[0]
        except Exception:
            return

        try:
            resp = await self.client.post(f"{API_URL}/adapters/{name}/start")
            log_panel.write_line(f"Start {name}: {resp.status_code}")
            await self.update_data()
        except Exception as e:
            log_panel.write_line(f"Failed to start {name}: {e}")

    async def action_stop_adapter(self) -> None:
        table = self.query_one(DataTable)
        log_panel = self.query_one(Log)
        
        if table.row_count == 0:
            return
        try:
            name = table.get_row_at(table.cursor_coordinate.row)[0]
        except Exception:
            return

        try:
            resp = await self.client.post(f"{API_URL}/adapters/{name}/stop")
            log_panel.write_line(f"Stop {name}: {resp.status_code}")
            await self.update_data()
        except Exception as e:
            log_panel.write_line(f"Failed to stop {name}: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        log_panel = self.query_one(Log)
        if event.button.id == "btn_connect":
            proxy_url = self.query_one("#input_proxy_url", Input).value
            server_id = self.query_one("#input_server_id", Input).value
            password = self.query_one("#input_password", Input).value
            
            if not proxy_url or not server_id or not password:
                log_panel.write_line("Please fill all connection fields.")
                return
                
            log_panel.write_line("Connecting...")
            try:
                resp = await self.client.post(f"{API_URL}/connection", json={
                    "proxy_url": proxy_url,
                    "server_id": server_id,
                    "password_code": password
                })
                if resp.status_code == 200:
                    log_panel.write_line("Connected successfully!")
                else:
                    log_panel.write_line(f"Connection failed: {resp.text}")
                await self.update_data()
            except Exception as e:
                log_panel.write_line(f"Connection error: {e}")
                
        elif event.button.id == "btn_disconnect":
            try:
                await self.client.post(f"{API_URL}/connection/disconnect")
                log_panel.write_line("Disconnected.")
                await self.update_data()
            except Exception as e:
                log_panel.write_line(f"Disconnect error: {e}")

if __name__ == "__main__":
    app = TellMomTUI()
    app.run()
