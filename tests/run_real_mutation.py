import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.trading.mutator import TradingStrategyMutator

async def run_mutation_demo():
    print("Starting strategy mutation demo...")
    
    mutator = TradingStrategyMutator()
    res = await mutator.mutate_strategies()
    
    print("\n=== STRATEGY MUTATION RESULT ===")
    import pprint
    pprint.pprint(res)
    print("================================")

if __name__ == "__main__":
    asyncio.run(run_mutation_demo())
