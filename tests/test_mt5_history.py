import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.trading.mt5_connector import MT5Connector
from autobot.trading.mutator import TradingStrategyMutator


def test_mt5_history_retrieval():
    mt5 = MT5Connector()
    mt5.connect()
    
    deals = mt5.get_historical_deals()
    assert len(deals) > 0
    assert deals[0]["ticket"] == 4829103
    assert deals[0]["symbol"] == "XAUUSD"
    
    rates = mt5.get_historical_rates("XAUUSD", "2026-07-20 14:30:00")
    assert len(rates) > 0
    assert rates[0]["open"] == 1950.0
    assert "indicators" in rates[0]
    
    print("test_mt5_history_retrieval passed.")


async def test_ea_loss_analysis():
    mutator = TradingStrategyMutator()
    res = await mutator.analyze_past_ea_trades()
    
    assert res is not None
    assert "status" in res
    assert res["status"] in ["completed", "skipped"]
    if res["status"] == "completed":
        assert res["analyzed_count"] > 0
        assert len(res["analyses"]) > 0
        print("Analyzed EA deals count:", res["analyzed_count"])
        
    print("test_ea_loss_analysis passed.")


async def main():
    test_mt5_history_retrieval()
    await test_ea_loss_analysis()
    print("All MT5 EA analysis tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
