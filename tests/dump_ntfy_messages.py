import asyncio
import json
import time
import httpx

async def main():
    url = "https://ntfy.sh/martinsharkey_autobot/json?poll=1&since=all"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        lines = resp.text.strip().split("\n")
        print(f"Retrieved {len(lines)} messages:")
        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                print(f"- Time: {data.get('time')} | Event: {data.get('event')} | Msg: {data.get('message')}")
            except Exception as e:
                print("Line parse error:", e)

if __name__ == "__main__":
    asyncio.run(main())
