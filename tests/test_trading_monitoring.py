import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.trading.monitoring import TradingMonitor, DASHBOARD_PATH, INSIGHTS_PATH
from autobot.trading.mutator import TradingStrategyMutator


def test_trading_monitoring_dashboard():
    monitor = TradingMonitor()
    
    # Log a mock winning trade
    monitor.log_trade(
        symbol="XAUUSD",
        action="buy",
        volume=0.1,
        profit=150.0,
        indicators={"RSI": 45, "MACD": 0.02},
        rationale="Crossover signal found on hourly chart"
    )
    
    # Log a mock losing trade to trigger mutation tests later
    monitor.log_trade(
        symbol="XAUUSD",
        action="sell",
        volume=0.1,
        profit=-80.0,
        indicators={"RSI": 78, "MACD": -0.05},
        rationale="Overbought bounce failure"
    )
    
    assert os.path.exists(DASHBOARD_PATH)
    assert os.path.exists(INSIGHTS_PATH)
    
    with open(INSIGHTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["total_trades"] >= 2
        assert data["win_rate"] > 0
        
    print("test_trading_monitoring_dashboard passed.")


async def test_strategy_mutator_triggers():
    mutator = TradingStrategyMutator()
    
    # Mutator should find our logged losing trade and analyze it
    res = await mutator.mutate_strategies()
    assert res is not None
    assert "status" in res
    # It will mock/trigger code mutation and spawn
    assert res["status"] in ["mutated", "skipped"]
    print("test_strategy_mutator_triggers passed.")


async def main():
    test_trading_monitoring_dashboard()
    await test_strategy_mutator_triggers()
    print("All trading monitoring and mutation tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
