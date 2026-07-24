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

    async def analyze_past_ea_trades(self) -> Dict[str, Any]:
        """Fetch historical EA trades from MT5, pull chart rates around their entry times, and analyze why they failed."""
        from autobot.trading.mt5_connector import MT5Connector
        mt5 = MT5Connector()
        mt5.connect()
        
        deals = mt5.get_historical_deals()
        if not deals:
            return {"status": "skipped", "reason": "no_historical_deals_found"}
            
        losses = [d for d in deals if d.get("profit", 0) < 0]
        if not losses:
            return {"status": "skipped", "reason": "no_losing_deals_found"}
            
        analyzed_count = 0
        analyses = []
        
        for loss in losses:
            symbol = loss.get("symbol", "XAUUSD")
            entry_time = loss.get("entry_time", "")
            ticket = loss.get("ticket", 0)
            
            rates = mt5.get_historical_rates(symbol, entry_time)
            rate_info = rates[0] if rates else {}
            indicators = rate_info.get("indicators", {})
            
            prompt = (
                f"You are executing an Expert Advisor (EA) trade analysis post-mortem.\n"
                f"EA Trade Ticket: {ticket} ({loss.get('comment')})\n"
                f"Symbol: {symbol} | Type: {loss.get('type')}\n"
                f"Entry Time: {entry_time} | Entry Price: {loss.get('entry_price')}\n"
                f"Exit Price: {loss.get('exit_price')} | Loss Amount: ${loss.get('profit')}\n"
                f"Chart Rates Candle at Entry: Open={rate_info.get('open')}, High={rate_info.get('high')}, Low={rate_info.get('low')}, Close={rate_info.get('close')}\n"
                f"Indicator States at Entry: {indicators}\n\n"
                f"Please analyze why this trade failed (e.g., was RSI overbought/oversold, was price moving against a major trend, etc.). "
                f"Provide a clear rule/lesson to prevent making this mistake in the future."
            )
            
            from autobot.consensus import MultiLLMConsensus
            consensus = MultiLLMConsensus()
            res = await consensus.get_consensus_response(prompt, judge_provider="google-ai-studio")
            analysis = res.get("consensus_text", "Failed to analyze.")
            
            self._runtime.get_memory().add(
                f"EA Post-Mortem Lesson for Ticket {ticket}: {analysis[:200]}...",
                source="trader",
                metadata={"ticket": ticket, "symbol": symbol, "loss": loss, "indicators": indicators, "analysis": analysis}
            )
            
            analyses.append({"ticket": ticket, "analysis": analysis})
            analyzed_count += 1
            
        return {
            "status": "completed",
            "analyzed_count": analyzed_count,
            "analyses": analyses
        }
