
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PlatformEntry:
    name: str
    adapter: Any = None
    config: Any = None
    label: str = ""
    adapter_factory: Any = None
    check_fn: Any = None


class PlatformRegistry:
    def __init__(self) -> None:
        self._platforms: dict[str, Any] = {}

    def register(self, name: str, adapter: Any) -> None:
        self._platforms[name] = adapter

    def get(self, name: str) -> Any:
        return self._platforms.get(name)


platform_registry = PlatformRegistry()
