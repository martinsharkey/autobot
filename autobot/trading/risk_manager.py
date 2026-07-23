
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, max_position_size: float = 0.1, max_drawdown: float = 0.2) -> None:
        self._max_position_size = max_position_size
        self._max_drawdown = max_drawdown
        self._current_drawdown = 0.0

    def validate_order(self, order: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any]:
        volume = float(order.get("volume", 0))
        if volume > self._max_position_size:
            return {"allowed": False, "reason": f"volume_exceeds_max_position_size:{self._max_position_size}"}
        equity = float(account.get("equity", 0))
        if equity <= 0:
            return {"allowed": False, "reason": "zero_equity"}
        return {"allowed": True}

    def update_drawdown(self, current_equity: float, peak_equity: float) -> Dict[str, Any]:
        if peak_equity <= 0:
            self._current_drawdown = 0.0
            return {"drawdown": 0.0, "action": "continue"}
        drawdown = max(0.0, (peak_equity - current_equity) / peak_equity)
        self._current_drawdown = drawdown
        if drawdown >= self._max_drawdown:
            return {"drawdown": drawdown, "action": "halt", "reason": "max_drawdown_reached"}
        return {"drawdown": drawdown, "action": "continue"}

    def get_risk_metrics(self) -> Dict[str, Any]:
        return {
            "max_position_size": self._max_position_size,
            "max_drawdown": self._max_drawdown,
            "current_drawdown": self._current_drawdown,
        }
