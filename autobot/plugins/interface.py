
from __future__ import annotations

import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


AUTOBOT_HOME = Path(__file__).resolve().parent.parent.parent.parent / "plugins"
_PLUGIN_DIRS = [AUTOBOT_HOME, Path.home() / ".autobot" / "plugins"]


class PluginInterface(ABC):
    @abstractmethod
    def load(self) -> None:
        pass

    @abstractmethod
    def unload(self) -> None:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def tool_definitions(self) -> List[Dict[str, Any]]:
        pass


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: Dict[str, PluginInterface] = {}

    def register(self, name: str, plugin: PluginInterface) -> None:
        plugin.load()
        self._plugins[name] = plugin

    def unregister(self, name: str) -> None:
        if name in self._plugins:
            self._plugins[name].unload()
            del self._plugins[name]

    def get(self, name: str) -> Optional[PluginInterface]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def health_checks(self) -> Dict[str, Dict[str, Any]]:
        return {name: plugin.health_check() for name, plugin in self._plugins.items()}

    def all_tool_definitions(self) -> List[Dict[str, Any]]:
        tools = []
        for plugin in self._plugins.values():
            tools.extend(plugin.tool_definitions())
        return tools

    def discover(self) -> int:
        count = 0
        for base in _PLUGIN_DIRS:
            if not base.exists():
                continue
            for path in base.iterdir():
                if not path.is_dir():
                    continue
                init = path / "__init__.py"
                if not init.exists():
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(path.name, str(init))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    plugin = getattr(mod, "plugin", None)
                    if plugin and isinstance(plugin, PluginInterface):
                        self.register(path.name, plugin)
                        count += 1
                except Exception:
                    continue
        return count
