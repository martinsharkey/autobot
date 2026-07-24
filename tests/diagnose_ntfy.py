import asyncio
import json
import httpx
import websockets

async def diagnose():
    uri = "wss://ntfy.sh/martinsharkey_autobot/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected to ntfy.sh WebSocket!")
            
            # Send a trigger message slightly after connection
            async def trigger():
                await asyncio.sleep(1.0)
                print("Publishing test message...")
                async with httpx.AsyncClient() as client:
                    await client.post("https://ntfy.sh/martinsharkey_autobot", content="diagnostic-ping")
            
            asyncio.create_task(trigger())
            
            # Read messages in loop for 4 seconds
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 4.0:
                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(raw_message)
                    print(f"Received event: {data.get('event')} -> message: {data.get('message')}")
                except asyncio.TimeoutError:
                    pass
    except Exception as exc:
        print(f"Connection failed: {exc}")

if __name__ == "__main__":
    asyncio.run(diagnose())
