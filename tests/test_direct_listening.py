import asyncio
import json
import httpx
import websockets

async def check_raw_messages():
    uri = "wss://ntfy.sh/martinsharkey_autobot/ws"
    print(f"Subscribing to raw events on {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            # Let's post a test message
            async def trigger_post():
                await asyncio.sleep(1.0)
                async with httpx.AsyncClient() as client:
                    await client.post("https://ntfy.sh/martinsharkey_autobot", content="test-raw-ping")
                    print("Test raw ping posted.")
            
            asyncio.create_task(trigger_post())
            
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 5.0:
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    print("RAW:", raw)
                except asyncio.TimeoutError:
                    pass
    except Exception as exc:
        print("Error:", exc)

if __name__ == "__main__":
    asyncio.run(check_raw_messages())
