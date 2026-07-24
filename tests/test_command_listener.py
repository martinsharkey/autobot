import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.llm import LLMClient

async def query_listener_solution():
    print("Initiating command listener query...")
    
    prompt = (
        "You are Autobot. Speak directly to Martin Sharkey.\n"
        "Martin wants you to be able to take commands from him on this same channel too (receiving and responding).\n"
        "Explain how you will achieve this, whether you need to mutate your code, and write the Python code for a background WebSocket listener "
        "that connects to ntfy.sh, parses commands, executes them via your local tools/runtime, and posts the results back to him."
    )
    
    client = LLMClient(direct=True)
    payload = {
        "messages": [
            {"role": "system", "content": "You are Autobot. Speak directly to Martin Sharkey, explaining how you will mutate to listen for and execute incoming commands over free channels."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        res = await client.chat_completions(payload)
        response = res["choices"][0]["message"]["content"]
        
        print("\n=== AUTOBOT COMMAND LISTENER RESPONSE ===")
        print(response)
        print("=========================================\n")
        
        # Save log
        log_path = Path("autobot_data/command_listener_log.md")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"# Autobot Command Listener & Mutation Plan\n\n{response}", encoding="utf-8")
        print(f"Plan log saved to {log_path}")
        
    except Exception as exc:
        print("Query failed:", exc)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(query_listener_solution())
