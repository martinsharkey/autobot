import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
import httpx
import websockets

logger = logging.getLogger(__name__)

TOPIC = "martinsharkey_autobot"
NTFY_SERVER = "wss://ntfy.sh"

async def handle_incoming_text(text: str) -> str:
    text = text.strip()
    if not text or text.startswith("[Autobot") or "CH4LL3NG3_S0LV3D" in text or "diagnostic-ping" in text:
        return ""
        
    # Check if this is a shell command or a general chat query
    is_cmd = False
    cmd_prefixes = ["dir", "whoami", "python", "git", "pip", "npm", "node", "ls", "cd", "echo"]
    first_word = text.split()[0].lower() if text.split() else ""
    if first_word in cmd_prefixes or text.startswith("."):
        is_cmd = True
        
    if is_cmd:
        try:
            cwd = str(Path(__file__).resolve().parent.parent.parent)
            result = subprocess.run(
                text,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=30
            )
            output = result.stdout + result.stderr
            return f"[Autobot Command Output]:\n{output.strip() or '[Success]'}"
        except Exception as e:
            return f"[Autobot Command Error]: {e}"
    else:
        # Query LLM to generate response
        from autobot.llm import LLMClient
        client = LLMClient(direct=True)
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": "You are Autobot. Speak directly to Martin Sharkey on this ntfy channel. Keep responses concise and smart."},
                    {"role": "user", "content": text}
                ]
            }
            res = await client.chat_completions(payload)
            response = res["choices"][0]["message"]["content"]
            return f"[Autobot Chat Reply]: {response}"
        except Exception as exc:
            return f"[Autobot Chat Error]: {exc}"
        finally:
            await client.close()

async def post_reply(message: str):
    url = f"https://ntfy.sh/{TOPIC}"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, content=message.encode('utf-8'))
    except Exception as exc:
        print(f"Failed to post ntfy reply: {exc}")

async def listen_loop():
    uri = f"{NTFY_SERVER}/{TOPIC}/ws"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Autobot daemon listening on {TOPIC} WebSocket...")
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
                        
                    if command.startswith("[Autobot") or "CH4LL3NG3_S0LV3D" in command or "diagnostic-ping" in command:
                        continue
                        
                    print(f"Received command: {command}")
                    output = await handle_incoming_text(command)
                    if output:
                        await post_reply(output)
        except Exception as e:
            print(f"Daemon socket error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen_loop())
