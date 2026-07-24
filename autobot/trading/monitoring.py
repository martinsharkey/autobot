from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv("AUTOBOT_HOME", ".")) / "autobot_data"
INSIGHTS_PATH = DATA_DIR / "trading_insights.json"
DASHBOARD_PATH = DATA_DIR / "trading_dashboard.md"


class TradingMonitor:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.insights = self._load_insights()

    def _load_insights(self) -> Dict[str, Any]:
        if INSIGHTS_PATH.exists():
            try:
                return json.loads(INSIGHTS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "demo_balance": 10000.0,
            "profit_loss": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "history": [],
            "symbol_insights": {
                "XAUUSD": {
                    "indicators": {"RSI": 50, "MACD": 0.0, "SMA_200": "above"},
                    "interactions": ["Negatively correlated with USD Index", "Positively correlated with EURUSD"],
                    "events": ["Fed Rate Decisions", "US CPI inflation releases"],
                    "performance": 0.0
                }
            }
        }

    def _save_insights(self) -> None:
        try:
            INSIGHTS_PATH.write_text(json.dumps(self.insights, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to save insights: %s", exc)

    def log_trade(self, symbol: str, action: str, volume: float, profit: float, indicators: Dict[str, Any], rationale: str) -> None:
        """Record trade details, indicators state, and final outcome to memory."""
        self.insights["total_trades"] += 1
        self.insights["profit_loss"] += profit
        self.insights["demo_balance"] += profit
        
        trade_record = {
            "trade_id": self.insights["total_trades"],
            "symbol": symbol,
            "action": action,
            "volume": volume,
            "profit": profit,
            "indicators": indicators,
            "rationale": rationale,
            "status": "win" if profit > 0 else "loss"
        }
        self.insights["history"].append(trade_record)
        
        # Calculate win rate
        wins = sum(1 for t in self.insights["history"] if t["status"] == "win")
        self.insights["win_rate"] = round(wins / len(self.insights["history"]), 2)
        
        # Update symbol stats
        if symbol not in self.insights["symbol_insights"]:
            self.insights["symbol_insights"][symbol] = {
                "indicators": {},
                "interactions": [],
                "events": [],
                "performance": 0.0
            }
        self.insights["symbol_insights"][symbol]["indicators"] = indicators
        self.insights["symbol_insights"][symbol]["performance"] += profit
        
        self._save_insights()
        self.compile_dashboard()

    def compile_dashboard(self) -> str:
        """Compile unstructured insights and logs into a markdown report dashboard."""
        history_lines = []
        for t in self.insights["history"][-5:]:
            history_lines.append(
                f"- **Trade #{t['trade_id']}**: {t['action'].upper()} {t['volume']} lots on {t['symbol']} "
                f"-> Profit: ${t['profit']:.2f} ({t['status'].upper()})\n  *Rationale*: {t['rationale']}"
            )
            
        symbol_lines = []
        for sym, stats in self.insights["symbol_insights"].items():
            ind_str = ", ".join(f"{k}={v}" for k, v in stats.get("indicators", {}).items()) or "None"
            inter_str = "\n  ".join(f"- {i}" for i in stats.get("interactions", [])) or "- No interactions mapped."
            events_str = ", ".join(stats.get("events", [])) or "None"
            symbol_lines.append(
                f"### {sym} Analysis\n"
                f"- **Active Indicators**: {ind_str}\n"
                f"- **Event Correlations**: {events_str}\n"
                f"- **Total Profit/Loss**: ${stats.get('performance', 0.0):.2f}\n"
                f"- **Interactions & Correlations**:\n  {inter_str}\n"
            )

        content = (
            f"# AUTOBOT Live Trading Dashboard\n\n"
            f"## Account Scorecard (Demo Account)\n"
            f"- **Account Status**: Always-On Active\n"
            f"- **Current Balance**: ${self.insights['demo_balance']:,.2f}\n"
            f"- **Net Profit/Loss**: ${self.insights['profit_loss']:,.2f}\n"
            f"- **Win Rate**: {self.insights['win_rate'] * 100:.1f}%\n"
            f"- **Total Trades Executed**: {self.insights['total_trades']}\n\n"
            f"## Symbol & Indicator Insights\n"
            f"{''.join(symbol_lines)}\n"
            f"## Recent Trade History\n"
            f"{''.join(history_lines) if history_lines else '- No trades logged yet.'}\n"
        )
        
        try:
            DASHBOARD_PATH.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to compile dashboard: %s", exc)
            
        return str(DASHBOARD_PATH)
