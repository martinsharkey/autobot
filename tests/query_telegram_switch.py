import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.llm import LLMClient

async def query_telegram_switch():
    print("Initiating Telegram switch query to Autobot...")
    
    prompt = (
        "You are Autobot. Speak directly to Martin Sharkey.\n"
        "Martin says: 'this service is strange. i can see the responses in the iphone ntfy app i just downloaded and they are coming on both topics that autobot created which is confusing however the iphone app doesnt allow me to reply. i dont see any notifications on the web version. maybe we should switch to telegram instead and i will assist autobot in getting it working. can you relay this to autobot'\n"
        "Please respond to Martin. Explain how you will transition your command and chat duplex listener from ntfy.sh to Telegram, "
        "and list exactly what credentials and configuration details you need from him to get the Telegram Bot running. "
        "Also, explain how you will implement a lightweight, zero-dependency Telegram listener using HTTP polling (getUpdates) in python."
    )
    
    client = LLMClient(direct=True)
    payload = {
        "messages": [
            {"role": "system", "content": "You are Autobot. Speak directly to Martin Sharkey, outlining the implementation and credentials required for the Telegram duplex chat transition."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        res = await client.chat_completions(payload)
        response = res["choices"][0]["message"]["content"]
        
        print("\n=== AUTOBOT TELEGRAM TRANSITION BLUEPRINT ===")
        print(response)
        print("=============================================\n")
        
        # Save log
        log_path = Path("autobot_data/telegram_transition_log.md")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"# Autobot Telegram Transition Blueprint\n\n{response}", encoding="utf-8")
        print(f"Blueprint log saved to {log_path}")
        
    except Exception as exc:
        print("Query failed:", exc)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(query_telegram_switch())
