import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
import httpx

# Add project root to search path to prevent ModuleNotFoundError
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

# Load env variables directly in case they were updated
def load_env():
    env_path = Path(_PROJECT_ROOT) / ".env"
    env_vars = {}
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()
    return env_vars

async def execute_command(command: str) -> str:
    try:
        cwd = str(_PROJECT_ROOT)
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

async def handle_incoming_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
        
    is_cmd = False
    cmd_prefixes = ["dir", "whoami", "python", "git", "pip", "npm", "node", "ls", "cd", "echo"]
    first_word = text.split()[0].lower() if text.split() else ""
    if first_word in cmd_prefixes or text.startswith("."):
        is_cmd = True
        
    if is_cmd:
        return await execute_command(text)
    else:
        # LLM query
        from autobot.llm import LLMClient
        client = LLMClient(direct=True)
        try:
            payload = {
                "messages": [
                    {"role": "system", "content": "You are Autobot, speaking directly to your master Martin Sharkey. Keep responses concise, analytical, and highly helpful."},
                    {"role": "user", "content": text}
                ]
            }
            res = await client.chat_completions(payload)
            response = res["choices"][0]["message"]["content"]
            return response
        except Exception as exc:
            return f"Chat Error: {exc}"
        finally:
            await client.close()

async def send_telegram_message(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

async def listen_loop():
    print("Initializing Autobot Telegram Daemon...")
    offset = 0
    
    while True:
        env = load_env()
        token = env.get("TELEGRAM_BOT_TOKEN")
        chat_id = env.get("TELEGRAM_CHAT_ID", "").strip()
        
        if not token:
            print("Telegram API token missing. Retrying in 10 seconds...")
            await asyncio.sleep(10)
            continue
            
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"offset": offset, "timeout": 20}
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=25.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update.get("update_id") + 1
                        message = update.get("message", {})
                        text = message.get("text", "").strip()
                        sender_chat = message.get("chat", {})
                        sender_id = str(sender_chat.get("id", ""))
                        
                        if not text:
                            continue
                            
                        # If chat ID is not yet locked, lock it to this sender (Martin Sharkey)
                        if not chat_id:
                            chat_id = sender_id
                            # Write to .env
                            env_path = Path(_PROJECT_ROOT) / ".env"
                            env_content = env_path.read_text(encoding="utf-8")
                            env_content = re.sub(r"TELEGRAM_CHAT_ID=.*", f"TELEGRAM_CHAT_ID={chat_id}", env_content)
                            env_path.write_text(env_content, encoding="utf-8")
                            print(f"LOCKED Telegram Chat ID to {chat_id}")
                            await send_telegram_message(token, chat_id, "LOCKED AND CONFIRMED. Autobot is now listening to you, Martin Sharkey!")
                            continue
                            
                        # Ignore unauthorized messages
                        if sender_id != chat_id:
                            print(f"Ignored unauthorized message from chat ID: {sender_id}")
                            continue
                            
                        print(f"Received Telegram command: '{text}' from {sender_id}")
                        response_text = await handle_incoming_text(text)
                        if response_text:
                            await send_telegram_message(token, chat_id, response_text)
                else:
                    print(f"Error fetching updates: {resp.status_code}")
        except Exception as exc:
            print(f"Telegram polling error: {exc}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen_loop())
