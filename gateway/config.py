
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class Platform(str, Enum):
    CLI = "cli"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEB = "web"
    VSCODE = "vscode"
    GOOGLE_CHAT = "google_chat"


class PlatformConfig:
    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class GatewayConfig:
    def __init__(self, raw: Dict[str, Any]) -> None:
        self._raw = raw

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)


def load_gateway_config() -> GatewayConfig:
    return GatewayConfig({})
