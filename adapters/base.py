from typing import Dict, Any, List, Callable
from pathlib import Path
import subprocess

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
