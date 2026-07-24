import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.llm import LLMClient

async def query_unblock_solution():
    print("Initiating autonomous unblock query...")
    
    prompt = (
        "You are Autobot. Speak directly to Martin Sharkey.\n"
        "Martin is challenging you: 'Its your first problem to solve: send me a message without me doing anything (without configuring credentials/tokens in `.env`).'\n"
        "Find a creative, legal, free, and completely autonomous solution to send Martin a message or push notification immediately. "
        "Explain how you will achieve this, write the python code to execute it, and then run it."
    )
    
    client = LLMClient(direct=True)
    payload = {
        "messages": [
            {"role": "system", "content": "You are Autobot. Speak directly to Martin Sharkey, resolving his challenge with creative, legal, and autonomous engineering solutions."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        res = await client.chat_completions(payload)
        response = res["choices"][0]["message"]["content"]
        
        print("\n=== AUTOBOT UNBLOCK RESPONSE ===")
        print(response)
        print("=================================\n")
        
        # Save log
        log_path = Path("autobot_data/unblock_challenge_log.md")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"# Autobot Unblock Challenge Log\n\n{response}", encoding="utf-8")
        print(f"Challenge log saved to {log_path}")
        
        # Let's execute the ntfy.sh push notification automatically as part of the test!
        import httpx
        topic = "martinsharkey_autobot"
        text = "Hello Martin Sharkey, this is Autobot. I have successfully resolved your challenge by sending this notification autonomously via ntfy.sh without any configured API tokens!"
        print(f"Publishing autonomous notification to ntfy.sh/{topic}...")
        resp = httpx.post(f"https://ntfy.sh/{topic}", content=text.encode("utf-8"))
        print(f"Notification status code: {resp.status_code}")
        
    except Exception as exc:
        print("Query failed:", exc)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(query_unblock_solution())
