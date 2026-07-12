import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Callable

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"

# ANSI colors for TUI
CLR_HEADER = "\033[95m"
CLR_BLUE = "\033[94m"
CLR_CYAN = "\033[96m"
CLR_GREEN = "\033[92m"
CLR_YELLOW = "\033[93m"
CLR_RED = "\033[91m"
CLR_RESET = "\033[0m"
CLR_BOLD = "\033[1m"


class AdapterPlugin:
    def __init__(
        self,
        name: str,
        display_name: str,
        default_config: Dict[str, Any],
        launch_fn: Callable[[Path, Dict[str, Any], Any], subprocess.Popen],
        description: str = "",
    ):
        self.name = name
        self.display_name = display_name
        self.default_config = default_config
        self.launch_fn = launch_fn
        self.description = description


class AdapterRegistry:
    def __init__(self):
        self.plugins: Dict[str, AdapterPlugin] = {}

    def register(self, plugin: AdapterPlugin) -> None:
        self.plugins[plugin.name] = plugin

    def get(self, name: str) -> AdapterPlugin:
        return self.plugins.get(name)

    def list_plugins(self) -> List[AdapterPlugin]:
        return list(self.plugins.values())


# Define Minecraft launcher
def launch_minecraft(base_dir: Path, cfg: Dict[str, Any], log_file: Any) -> subprocess.Popen:
    script_path = base_dir / "minecraft" / "minecraft.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--log",
        cfg["log_path"],
        "--server-id",
        cfg["server_id"]
    ]
    if cfg.get("backend_url"):
        cmd.extend(["--backend-url", cfg["backend_url"]])
    if cfg.get("proxy_url"):
        cmd.extend(["--proxy-url", cfg["proxy_url"]])
    if cfg.get("password_code"):
        cmd.extend(["--password-code", cfg["password_code"]])
    if cfg.get("poll_interval"):
        cmd.extend(["--poll-interval", str(cfg["poll_interval"])])
    if cfg.get("max_retries"):
        cmd.extend(["--max-retries", str(cfg["max_retries"])])

    return subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(base_dir),
    )


# Create and populate registry
from .base import AdapterRegistry
from .minecraft_adapter import plugin as minecraft_plugin

registry = AdapterRegistry()
registry.register(minecraft_plugin)


class TUI:
    def __init__(self):
        self.config = self.load_config()
        self.processes: Dict[str, subprocess.Popen] = {}

    def load_config(self) -> Dict[str, Any]:
        cfg = {}
        # Populate with default config from registry
        for plugin in registry.list_plugins():
            cfg[plugin.name] = plugin.default_config.copy()

        if CONFIG_FILE.exists():
            try:
                user_cfg = json.loads(CONFIG_FILE.read_text())
                for name, default_val in cfg.items():
                    if name in user_cfg:
                        default_val.update(user_cfg[name])
            except Exception:
                pass
        return cfg

    def save_config(self) -> None:
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, indent=2))
        except Exception as e:
            print(f"{CLR_RED}Failed to save config: {e}{CLR_RESET}")

    def check_processes(self) -> None:
        for name, proc in list(self.processes.items()):
            if proc.poll() is not None:
                self.processes.pop(name)

    def start_plugin(self, name: str) -> None:
        self.check_processes()
        if name in self.processes:
            print(f"{CLR_YELLOW}{name.capitalize()} is already running.{CLR_RESET}")
            time.sleep(1)
            return

        plugin = registry.get(name)
        if not plugin:
            print(f"{CLR_RED}Unknown plugin: {name}{CLR_RESET}")
            time.sleep(1)
            return

        base_dir = Path(__file__).resolve().parent
        log_file_path = base_dir / f"{name}_output.log"
        log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")

        try:
            cfg = self.config[name]
            proc = plugin.launch_fn(base_dir, cfg, log_file)
            self.processes[name] = proc
            print(f"{CLR_GREEN}Started {plugin.display_name} (PID: {proc.pid}){CLR_RESET}")
        except Exception as e:
            print(f"{CLR_RED}Failed to start {plugin.display_name}: {e}{CLR_RESET}")
        
        time.sleep(1)

    def stop_plugin(self, name: str) -> None:
        if name not in self.processes:
            print(f"{CLR_YELLOW}{name.capitalize()} is not running.{CLR_RESET}")
            time.sleep(1)
            return

        proc = self.processes[name]
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        self.processes.pop(name, None)
        print(f"{CLR_RED}Stopped {name.capitalize()} adapter.{CLR_RESET}")
        time.sleep(1)

    def view_logs(self, name: str) -> None:
        base_dir = Path(__file__).resolve().parent
        log_file_path = base_dir / f"{name}_output.log"
        
        if not log_file_path.exists():
            print(f"{CLR_YELLOW}No log output available for {name} yet.{CLR_RESET}")
            input("\nPress Enter to return...")
            return

        print(f"\n{CLR_BOLD}{CLR_CYAN}--- {name.upper()} ADAPTER LOGS (Last 30 lines) ---{CLR_RESET}")
        try:
            lines = log_file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-30:]:
                print(line)
        except Exception as e:
            print(f"{CLR_RED}Could not read log file: {e}{CLR_RESET}")
        
        input("\nPress Enter to return...")

    def edit_config(self, name: str) -> None:
        cfg = self.config.get(name)
        if cfg is None:
            print(f"{CLR_RED}Unknown plugin: {name}{CLR_RESET}")
            time.sleep(1)
            return
        keys = list(cfg.keys())

        while True:
            self.clear_screen()
            print(f"{CLR_BOLD}{CLR_HEADER}=================================================={CLR_RESET}")
            print(f"       {CLR_BOLD}Configure {name.capitalize()} Adapter{CLR_RESET}")
            print(f"{CLR_BOLD}{CLR_HEADER}=================================================={CLR_RESET}")
            
            for idx, key in enumerate(keys, 1):
                disp_val = cfg[key]
                if key in ["bot_token", "password_code"] and disp_val:
                    disp_val = "*" * min(len(disp_val), 12) + " (hidden)"
                
                print(f"  {CLR_CYAN}{idx}. {key.replace('_', ' ').title()}:{CLR_RESET} {disp_val}")
            
            print(f"\n  {CLR_GREEN}S. Save & Return{CLR_RESET}")
            print(f"  {CLR_RED}C. Cancel Changes & Return{CLR_RESET}")
            print(f"{CLR_BOLD}{CLR_HEADER}--------------------------------------------------{CLR_RESET}")
            
            choice = input("Select an option (or number to edit): ").strip().lower()
            
            if choice == "s":
                self.save_config()
                break
            elif choice == "c":
                self.config = self.load_config() # Reload from disk
                break
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(keys):
                    key = keys[idx]
                    current_val = cfg[key]
                    print(f"\nEditing {CLR_BOLD}{key}{CLR_RESET}")
                    new_val = input(f"Enter new value (current: '{current_val}'): ").strip()
                    cfg[key] = new_val
                else:
                    print(f"{CLR_RED}Invalid option number.{CLR_RESET}")
                    time.sleep(1)
            else:
                print(f"{CLR_RED}Invalid choice.{CLR_RESET}")
                time.sleep(1)

    def clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def run(self) -> None:
        while True:
            self.check_processes()
            self.clear_screen()
            
            print(f"{CLR_BOLD}{CLR_HEADER}=================================================={CLR_RESET}")
            print(f"         {CLR_BOLD}TellMom Adapter Central TUI{CLR_RESET}")
            print(f"{CLR_BOLD}{CLR_HEADER}=================================================={CLR_RESET}")
            
            plugins = registry.list_plugins()
            for idx, plugin in enumerate(plugins, 1):
                is_run = plugin.name in self.processes
                status = f"{CLR_GREEN}RUNNING (PID: {self.processes[plugin.name].pid}){CLR_RESET}" if is_run else f"{CLR_RED}STOPPED{CLR_RESET}"
                print(f" {CLR_BOLD}{idx}. {plugin.display_name}:{CLR_RESET} [{status}]")
                print(f"    - Description: {plugin.description}")
                
                # Show key configurations
                for key, val in self.config[plugin.name].items():
                    if key in ["log_path", "server_id", "bot_token"]:
                        disp_val = val
                        if key == "bot_token" and val:
                            disp_val = "Configured"
                        print(f"    - {key.replace('_', ' ').title()}: {disp_val}")
                print()
            
            print(f"{CLR_BOLD}{CLR_HEADER}--------------------------------------------------{CLR_RESET}")
            print(f" {CLR_BOLD}Commands:{CLR_RESET}")
            
            # Print dynamically based on available plugins
            available_names = "|".join([p.name for p in plugins])
            print(f"  {CLR_CYAN}start <{available_names}>{CLR_RESET}   - Start the selected adapter")
            print(f"  {CLR_CYAN}stop <{available_names}>{CLR_RESET}    - Stop the selected adapter")
            print(f"  {CLR_CYAN}config <{available_names}>{CLR_RESET}  - Edit adapter configuration")
            print(f"  {CLR_CYAN}logs <{available_names}>{CLR_RESET}    - View last log output")
            print(f"  {CLR_RED}exit{CLR_RESET}            - Exit TUI (stops all running adapters)")
            print(f"{CLR_BOLD}{CLR_HEADER}=================================================={CLR_RESET}")
            
            try:
                cmd_line = input("> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                cmd_line = "exit"
            
            if not cmd_line:
                continue

            parts = cmd_line.split()
            cmd = parts[0]
            target = parts[1] if len(parts) > 1 else None

            # Map abbreviations or direct name
            if target:
                mapped_target = None
                for p in plugins:
                    if target in [p.name, p.name[:2]]:
                        mapped_target = p.name
                        break
                target = mapped_target

            if cmd == "exit":
                print("\nShutting down adapters...")
                for name in list(self.processes.keys()):
                    self.stop_plugin(name)
                print("Exiting.")
                break
            
            elif cmd == "start":
                if target:
                    self.start_plugin(target)
                else:
                    print(f"{CLR_RED}Please specify an adapter.{CLR_RESET}")
                    time.sleep(1)

            elif cmd == "stop":
                if target:
                    self.stop_plugin(target)
                else:
                    print(f"{CLR_RED}Please specify an adapter.{CLR_RESET}")
                    time.sleep(1)

            elif cmd == "config":
                if target:
                    self.edit_config(target)
                else:
                    print(f"{CLR_RED}Please specify an adapter.{CLR_RESET}")
                    time.sleep(1)

            elif cmd == "logs":
                if target:
                    self.view_logs(target)
                else:
                    print(f"{CLR_RED}Please specify an adapter.{CLR_RESET}")
                    time.sleep(1)
            
            else:
                print(f"{CLR_RED}Unknown command: {cmd}{CLR_RESET}")
                time.sleep(1)


if __name__ == "__main__":
    tui = TUI()
    tui.run()
