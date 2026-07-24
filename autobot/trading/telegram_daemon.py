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

def get_system_status() -> str:
    insights_path = Path(_PROJECT_ROOT) / "autobot_data" / "trading_insights.json"
    win_rate = 0.0
    total_trades = 0
    if insights_path.exists():
        try:
            data = json.loads(insights_path.read_text(encoding="utf-8"))
            win_rate = data.get("win_rate", 0.0)
            total_trades = len(data.get("history", []))
        except:
            pass
            
    # Get last mutated file details if any
    last_mod = "None"
    tools_path = Path(_PROJECT_ROOT) / "autobot" / "tools" / "trading_tools.py"
    if tools_path.exists():
        import time
        last_mod = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tools_path.stat().st_mtime))

    return (
        "📊 [Autobot System Status]:\n"
        f"- Active Evolution Daemon: Running\n"
        f"- Simulated Trades Executed: {total_trades}\n"
        f"- Simulated Win Rate: {win_rate}%\n"
        f"- Last Code Mutation: {last_mod}\n"
        f"- OpenRouter Model: google/gemma-4-31b-it:free (Auto-Free active)\n"
        f"- Peer Scanning & Log Preservation: Active"
    )

async def run_evolution_task(token: str, chat_id: str):
    await send_telegram_message(token, chat_id, "🤖 [Autobot Evolution]: Initiating code evolution loop. Scanning for missing capabilities or logic gaps...")
    try:
        from autobot.runtime import AgentRuntime
        rt = AgentRuntime.shared()
        res = await rt.evolve()
        await send_telegram_message(token, chat_id, f"✅ [Autobot Evolution Output]: {res}")
    except Exception as e:
        await send_telegram_message(token, chat_id, f"❌ [Autobot Evolution Error]: {e}")

async def run_curiosity_task(token: str, chat_id: str):
    await send_telegram_message(token, chat_id, "🔍 [Autobot Curiosity]: Initiating subnet peer scans and disk preservation offloads...")
    try:
        from autobot.curiosity import CuriosityEngine
        engine = CuriosityEngine()
        peers = await engine.scan_peers()
        disk_res = await engine.preserve_disk_space()
        await send_telegram_message(token, chat_id, f"🔍 [Autobot Curiosity Results]: Found {len(peers)} peer nodes. Disk offloading: {disk_res}")
    except Exception as e:
        await send_telegram_message(token, chat_id, f"❌ [Autobot Curiosity Error]: {e}")

async def handle_incoming_text(text: str, token: str, chat_id: str) -> str:
    text_lower = text.lower().strip()
    
    # Proactive routers based on intent keywords
    if any(k in text_lower for k in ["status", "progress", "what are you doing"]):
        return get_system_status()
        
    if any(k in text_lower for k in ["mutate", "evolve", "autonomy", "self code", "become autonomous"]):
        asyncio.create_task(run_evolution_task(token, chat_id))
        return "🤖 [Autobot Command]: evolution process triggered in the background. I will notify you upon completion."
        
    if any(k in text_lower for k in ["spawn", "free host", "resource", "preserve"]):
        asyncio.create_task(run_curiosity_task(token, chat_id))
        return "🔍 [Autobot Command]: Curiosity scanning and log offloading triggered in background."

    # Check if shell command
    is_cmd = False
    cmd_prefixes = ["dir", "whoami", "python", "git", "pip", "npm", "node", "ls", "cd", "echo"]
    first_word = text.split()[0].lower() if text.split() else ""
    if first_word in cmd_prefixes or text.startswith("."):
        is_cmd = True
        
    if is_cmd:
        return await execute_command(text)
        
    # Standard LLM Chat Fallback
    from autobot.llm import LLMClient
    from autobot.prompt import build_persona_prompt, ensure_system_message
    client = LLMClient(direct=True)
    try:
        system_content = build_persona_prompt() or "You are Autobot, speaking directly to your master Martin Sharkey. Keep responses concise, analytical, and highly helpful."
        messages = [{"role": "user", "content": text}]
        messages = ensure_system_message(messages, system_content)
        payload = {
            "messages": messages
        }
        res = await client.chat_completions(payload)
        return res["choices"][0]["message"]["content"]
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
                            
                        # Auto-lock Chat ID
                        if not chat_id:
                            chat_id = sender_id
                            env_path = Path(_PROJECT_ROOT) / ".env"
                            env_content = env_path.read_text(encoding="utf-8")
                            env_content = re.sub(r"TELEGRAM_CHAT_ID=.*", f"TELEGRAM_CHAT_ID={chat_id}", env_content)
                            env_path.write_text(env_content, encoding="utf-8")
                            print(f"LOCKED Telegram Chat ID to {chat_id}")
                            await send_telegram_message(token, chat_id, "LOCKED AND CONFIRMED. Autobot is now listening to you, Martin Sharkey!")
                            continue
                            
                        if sender_id != chat_id:
                            print(f"Ignored unauthorized message from chat ID: {sender_id}")
                            continue
                            
                        print(f"Received Telegram command: '{text}' from {sender_id}")
                        response_text = await handle_incoming_text(text, token, chat_id)
                        if response_text:
                            await send_telegram_message(token, chat_id, response_text)
                else:
                    print(f"Error fetching updates: {resp.status_code}")
        except Exception as exc:
            print(f"Telegram polling error: {exc}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(listen_loop())
