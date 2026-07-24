import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
import httpx
import websockets

logger = logging.getLogger(__name__)

LISTEN_TOPIC = "martinsharkey_autobot"
REPLY_TOPIC = "martinsharkey_autobot_reply"
NTFY_SERVER = "wss://ntfy.sh"

def execute_command(command: str) -> str:
    # Filter out empty or self-messages
    if not command or command.startswith("[Autobot") or "CH4LL3NG3_S0LV3D" in command:
        return ""
    try:
        # Run command inside workspace folder
        cwd = str(Path(__file__).resolve().parent.parent.parent)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        output = result.stdout + result.stderr
        return output.strip() or "[Command executed successfully]"
    except Exception as e:
        return f"Error: {str(e)}"

async def post_reply(message: str):
    url = f"https://ntfy.sh/{REPLY_TOPIC}"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, content=message.encode('utf-8'))
    except Exception as exc:
        print(f"Failed to post ntfy reply: {exc}")

async def listen_loop():
    uri = f"{NTFY_SERVER}/{LISTEN_TOPIC}/ws"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Autobot daemon listening on {LISTEN_TOPIC} WebSocket...")
                async for raw_message in websocket:
                    try:
                        data = json.loads(raw_message)
                        if data.get("event") != "message":
                            continue
                        command = data.get("message", "").strip()
                    except Exception:
                        command = raw_message.strip()

                    if not command:
                        continue
                        
                    if command.startswith("[Autobot") or "CH4LL3NG3_S0LV3D" in command:
                        continue
                        
                    print(f"Received command: {command}")
                    output = execute_command(command)
                    if output:
                        reply = f"[Autobot Reply to '{command[:20]}']:\n{output}"
                        await post_reply(reply)
        except Exception as e:
            print(f"Daemon socket error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen_loop())
