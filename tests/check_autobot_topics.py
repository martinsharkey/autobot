import asyncio
import json
import httpx

async def check_topic(topic):
    url = f"https://ntfy.sh/{topic}/json?poll=1"
    print(f"Checking {topic}...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        lines = resp.text.strip().split("\n")
        print(f"Topic {topic} has {len(lines)} messages:")
        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                print(f"- {data.get('message')}")
            except Exception:
                pass

async def main():
    await check_topic("autobot-martin-cmd")
    await check_topic("autobot-martin-reply")

if __name__ == "__main__":
    asyncio.run(main())
