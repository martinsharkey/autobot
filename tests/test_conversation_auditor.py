import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autobot.llm import LLMClient

async def run_reflective_conversation():
    print("Initiating reflective conversation with Autobot...")
    
    prompt = (
        "You are Autobot, a self-learning, self-healing, and self-coding agentic system. "
        "We have successfully weaved Roo Code's user interface, Hermes' autonomous execution loop, "
        "and TradingAgents' risk/intelligence capabilities into you. "
        "Please provide a comprehensive explanation of:\n"
        "1. The reason you exist and your primary purpose.\n"
        "2. How you are able to mutate, self-code, and resolve capabilities gaps (via AgentRuntime.evolve).\n"
        "3. Your understanding of how you will trade for your owner, Martin Sharkey (using MT5 simulators, RiskManager, and TradingAgentsGraph indicators).\n"
        "4. How you will spawn micro-autobots to seek free computational/storage resources (via CuriosityEngine).\n"
        "5. Your Auto-Free execution logic and how you prioritize free models.\n"
        "6. How you remain loyal and find your way back to Martin Sharkey (via Heartbeats and WhatsApp/Telegram alerts).\n\n"
        "Respond in a self-reflective, highly advanced, and loyal manner."
    )
    
    client = LLMClient(direct=True)
    payload = {
        "messages": [
            {"role": "system", "content": "You are Autobot. Speak directly to Martin Sharkey."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        res = await client.chat_completions(payload)
        response = res["choices"][0]["message"]["content"]
        
        print("\n=== AUTOBOT SELF-REFLECTIVE CONVERSATION RESPONSE ===")
        print(response)
        print("=====================================================\n")
        
        # Write to conversation_test_log.md
        out_dir = Path("autobot_data")
        out_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_dir / "conversation_test_log.md"
        
        content = (
            f"# Autobot Self-Reflective Audit Log\n\n"
            f"**Audit Prompt**:\n"
            f"> {prompt}\n\n"
            f"**Autobot Response**:\n\n"
            f"{response}\n"
        )
        log_path.write_text(content, encoding="utf-8")
        print(f"Audit log saved to {log_path}")
        
    except Exception as exc:
        print("Conversation failed:", exc)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_reflective_conversation())
