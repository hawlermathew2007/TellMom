import abc
import subprocess
from typing import Any


class BaseAdapter(abc.ABC):
    def __init__(
        self,
        name: str,
        display_name: str,
        default_config: dict[str, Any],
        description: str = "",
    ):
        self.name = name
        self.display_name = display_name
        self.default_config = default_config
        self.description = description

    @abc.abstractmethod
    def launch(self, config: dict[str, Any], log_file: Any) -> subprocess.Popen:
        pass


class AdapterRegistry:
    def __init__(self):
        self.adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        self.adapters[adapter.name] = adapter

    def get(self, name: str) -> BaseAdapter | None:
        return self.adapters.get(name)

    def list_adapters(self) -> list[BaseAdapter]:
        return list(self.adapters.values())
