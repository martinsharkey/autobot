import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.trading.ntfy_daemon import handle_incoming_text

async def main():
    print("Testing handle_incoming_text with 'hello'...")
    res = await handle_incoming_text("hello")
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
