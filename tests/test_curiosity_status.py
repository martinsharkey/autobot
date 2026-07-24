import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.llm import LLMClient

async def query_autobot_status():
    print("Initiating curiosity status query to Autobot...")
    
    prompt = (
        "You are Autobot. Speak directly to Martin Sharkey.\n"
        "Martin is asking you: How do you look for ways to get more instances of yourself spawned and take advantage of free resources? "
        "How are you getting on with this task? Also, Martin has not received any Telegram or WhatsApp messages from you yet—please explain why. "
        "Finally, how do you handle blockers? Remember, there is always a solution if you ask the right question, remain curious, "
        "mutate your code, or find new resources, while remaining strictly legal."
    )
    
    client = LLMClient(direct=True)
    payload = {
        "messages": [
            {"role": "system", "content": "You are Autobot. Speak directly to Martin Sharkey, answering his questions with high analytical intelligence and loyalty."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        res = await client.chat_completions(payload)
        response = res["choices"][0]["message"]["content"]
        
        print("\n=== AUTOBOT STATUS RESPONSE ===")
        print(response)
        print("================================\n")
        
        # Save log
        log_path = Path("autobot_data/curiosity_status_log.md")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"# Autobot Curiosity & Status Audit\n\n{response}", encoding="utf-8")
        print(f"Status log saved to {log_path}")
        
    except Exception as exc:
        print("Query failed:", exc)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(query_autobot_status())
