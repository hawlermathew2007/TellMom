import os
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Log
from textual.binding import Binding

from adapters.base import AdapterRegistry
from adapters.minecraft.minecraft import plugin as minecraft_plugin

CONFIG_FILE = Path(__file__).resolve().parent / ("config.yaml" if HAS_YAML else "config.json")

registry = AdapterRegistry()
registry.register(minecraft_plugin)

class TellMomApp(App):
    CSS = """
    DataTable {
        height: 2fr;
        border: solid green;
    }
    Log {
        height: 1fr;
        border: solid blue;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "start_adapter", "Start"),
        Binding("x", "stop_adapter", "Stop"),
    ]

    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.processes = {}

    def load_config(self):
        cfg = {}

        # Register default config
        for adapter in registry.list_adapters():
            cfg[adapter.name] = adapter.default_config.copy()
            
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    user_cfg = yaml.safe_load(f) if HAS_YAML else json.load(f)
                if user_cfg:
                    for name, default_val in cfg.items():
                        if name in user_cfg:
                            default_val.update(user_cfg[name])
            except Exception:
                pass
        return cfg

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                if HAS_YAML:
                    yaml.dump(self.config, f)
                else:
                    json.dump(self.config, f, indent=2)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(id="adapters_table")
        yield Log(id="logs_panel")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Status", "Description", "Server ID", "Proxy/DH State")
        self.update_table()
        self.set_interval(1.0, self.update_table)

    def update_table(self) -> None:
        table = self.query_one(DataTable)
        
        # Save cursor position before clear
        row = table.cursor_coordinate.row
        
        table.clear()
        
        for adapter in registry.list_adapters():
            name = adapter.name
            is_running = name in self.processes and self.processes[name].poll() is None
            
            if name in self.processes and self.processes[name].poll() is not None:
                self.processes.pop(name)
                is_running = False
                
            status = "[green]RUNNING[/]" if is_running else "[red]STOPPED[/]"
            
            cfg = self.config.get(name, {})
            server_id = cfg.get("server_id", "None")
            
            proxy_state = "No Proxy"
            if cfg.get("proxy_url"):
                proxy_state = "Associated (Configured)"
            
            table.add_row(name, status, adapter.description, server_id, proxy_state)

        # Restore cursor
        if row < table.row_count:
            table.move_cursor(row=row)

    def action_start_adapter(self) -> None:
        table = self.query_one(DataTable)
        log_panel = self.query_one(Log)
        
        if table.row_count == 0:
            return
            
        try:
            name = table.get_row_at(table.cursor_coordinate.row)[0]
        except Exception:
            return

        if name in self.processes:
            log_panel.write_line(f"{name} is already running.")
            return

        adapter = registry.get(name)
        if not adapter:
            return

        base_dir = Path(__file__).resolve().parent
        log_file_path = base_dir / f"{name}_output.log"
        log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")
        
        cfg = self.config[name]
        try:
            proc = adapter.launch(base_dir, cfg, log_file)
            self.processes[name] = proc
            log_panel.write_line(f"Started {name} (PID: {proc.pid})")
        except Exception as e:
            log_panel.write_line(f"Failed to start {name}: {e}")
        
        self.update_table()

    def action_stop_adapter(self) -> None:
        table = self.query_one(DataTable)
        log_panel = self.query_one(Log)
        
        if table.row_count == 0:
            return
            
        try:
            name = table.get_row_at(table.cursor_coordinate.row)[0]
        except Exception:
            return

        if name not in self.processes:
            log_panel.write_line(f"{name} is not running.")
            return

        proc = self.processes[name]
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        self.processes.pop(name, None)
        log_panel.write_line(f"Stopped {name}.")
        self.update_table()

if __name__ == "__main__":
    app = TellMomApp()
    app.run()
