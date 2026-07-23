
from __future__ import annotations

import threading
from typing import Any, Dict


def acquire_scoped_lock(key: str, ttl_seconds: int = 60) -> bool:
    return False


class GatewayStatus:
    def __init__(self) -> None:
        self._status: Dict[str, Any] = {}
        self._locks: Dict[str, bool] = {}

    def set_status(self, key: str, value: Any) -> None:
        self._status[key] = value

    def get_status(self, key: str, default: Any = None) -> Any:
        return self._status.get(key, default)


gateway_status = GatewayStatus()
