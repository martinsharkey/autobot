import asyncio
import json
import httpx
import websockets

async def test_end_to_end_ntfy():
    uri = "wss://ntfy.sh/martinsharkey_autobot/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected! Sending a test message 'hello'...")
            
            # Post 'hello' to the topic
            async def trigger_post():
                await asyncio.sleep(1.0)
                async with httpx.AsyncClient() as client:
                    await client.post("https://ntfy.sh/martinsharkey_autobot", content="hello")
                    print("Posted 'hello' successfully.")
            
            asyncio.create_task(trigger_post())
            
            # Read messages and print them
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < 8.0:
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(raw)
                    print(f"EVENT: {data.get('event')} | message: {data.get('message')}")
                except asyncio.TimeoutError:
                    pass
    except Exception as exc:
        print("Error:", exc)

if __name__ == "__main__":
    asyncio.run(test_end_to_end_ntfy())
