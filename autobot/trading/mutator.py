from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from autobot.trading.monitoring import INSIGHTS_PATH, TradingMonitor
from autobot.runtime import AgentRuntime

logger = logging.getLogger(__name__)


class TradingStrategyMutator:
    def __init__(self) -> None:
        self.monitor = TradingMonitor()
        self._runtime = AgentRuntime.shared()

    async def mutate_strategies(self) -> Dict[str, Any]:
        """Review trading performance and spawn a coder sub-agent to optimize strategy logic."""
        insights = self.monitor.insights
        history = insights.get("history", [])
        
        # Look for the latest losing trade to analyze its parameters
        losses = [t for t in history if t.get("status") == "loss"]
        if not losses:
            return {"status": "skipped", "reason": "no_losses_logged"}
            
        latest_loss = losses[-1]
        symbol = latest_loss.get("symbol", "XAUUSD")
        indicators = latest_loss.get("indicators", {})
        rationale = latest_loss.get("rationale", "")
        
        logger.info("Analyzing latest losing trade for %s, indicators=%s", symbol, indicators)
        
        # Formulate mutation instructions
        goal = (
            f"You are executing an autonomous trading strategy mutation task.\n"
            f"A losing trade was recorded for symbol {symbol} with the following indicators:\n"
            f"{indicators}\n\n"
            f"Rationale: {rationale}\n\n"
            f"Please optimize our trading strategy rules. Mutate the entry/exit thresholds "
            f"in autobot/tools/trading_tools.py to avoid placing trades under these exact indicator conditions. "
            f"Write clean, correct code, run tests to verify the changes, and update the license baseline."
        )
        
        # Spawn isolated coder agent to rewrite the strategy parameters!
        result = await self._runtime.spawn(goal, mode="coder")
        
        # Recalculate baseline hashes since we mutated code files
        from autobot.license import install_license
        try:
            install_license('test-key-123')
        except Exception:
            pass
            
        return {
            "status": "mutated",
            "symbol": symbol,
            "loss_analyzed": latest_loss,
            "coder_result": result
        }
