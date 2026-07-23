
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MT5Connector:
    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self._host = host
        self._port = port
        self._connected = False

    def connect(self) -> Dict[str, Any]:
        self._connected = True
        return {"status": "connected", "host": self._host, "port": self._port}

    def disconnect(self) -> Dict[str, Any]:
        self._connected = False
        return {"status": "disconnected"}

    def get_account_info(self) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "not_connected"}
        return {"balance": 0.0, "equity": 0.0, "margin": 0.0, "free_margin": 0.0}

    def place_order(self, symbol: str, volume: float, order_type: str = "buy") -> Dict[str, Any]:
        if not self._connected:
            return {"error": "not_connected"}
        return {"status": "simulated", "symbol": symbol, "volume": volume, "type": order_type}

    def get_positions(self) -> Dict[str, Any]:
        if not self._connected:
            return {"error": "not_connected"}
        return {"positions": []}
