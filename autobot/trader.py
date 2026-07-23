
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from autobot.memory import MemoryStore

_TRADING_BASE = Path(__file__).resolve().parent.parent.parent / "trading-repo" / "tradingagents"
if str(_TRADING_BASE.parent) not in sys.path:
    sys.path.insert(0, str(_TRADING_BASE.parent))

for _key in list(sys.modules):
    if _key == "tradingagents" or _key.startswith("tradingagents."):
        del sys.modules[_key]


class TradingAgentsBridge:
    def __init__(self, memory: Optional[MemoryStore] = None) -> None:
        self.memory = memory or MemoryStore()
        self._graph = None

    def _ensure_graph(self) -> None:
        if self._graph is not None:
            return
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        config = dict(DEFAULT_CONFIG)
        config["llm_provider"] = "deepseek"
        config["deep_think_llm"] = "deepseek-chat"
        config["quick_think_llm"] = "deepseek-chat"
        config["backend_url"] = ""
        self._graph = TradingAgentsGraph(
            selected_analysts=("market", "news", "fundamentals"),
            debug=False,
            config=config,
        )

    def run_research(self, ticker: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_graph()
        today = trade_date or __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        try:
            final_state = self._graph.propagate(company_name=ticker, trade_date=today, asset_type="stock")
            result = {
                "ticker": ticker,
                "trade_date": today,
                "status": "completed",
                "final_state": final_state,
            }
            self.memory.add(f"Research {ticker} for {today}", source="trader", metadata={"ticker": ticker})
            return result
        except Exception as exc:
            return {"ticker": ticker, "trade_date": today, "status": "failed", "error": str(exc)}

    def process_signal(self, full_signal: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_graph()
        try:
            processed = self._graph.process_signal(full_signal)
            return {"status": "ok", "processed": processed}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def save_reports(self, final_state: Any, ticker: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_graph()
        try:
            path = self._graph.save_reports(final_state, ticker, save_path=save_path)
            return {"status": "ok", "path": str(path)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
