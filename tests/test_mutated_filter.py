import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.tools.trading_tools import handle_place_mt5_trade

def test_mutated_rsi_filter():
    # Call order placement for a sell. The mock MT5 connector returns RSI=75 for entry_time query
    # and this should trigger the new self-mutated safety block!
    res = handle_place_mt5_trade({"symbol": "XAUUSD", "action": "sell", "volume": 0.1})
    print("Response from mutated trade placement:", res)
    assert "Trade REJECTED: Overbought condition detected" in res
    print("test_mutated_rsi_filter passed successfully!")

if __name__ == "__main__":
    test_mutated_rsi_filter()
