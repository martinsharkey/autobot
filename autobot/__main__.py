import asyncio
import argparse
import os
from pathlib import Path

from autobot.agent import AutobotAgent
from autobot.config import Config
from autobot.llm import LLMClient


async def repl(agent: AutobotAgent):
    print("AUTOBOT REPL — type 'quit' to exit, 'mode <name>' to switch modes")
    while True:
        try:
            goal = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not goal:
            continue
        if goal.lower() in {"quit", "exit"}:
            break
        if goal.lower().startswith("mode "):
            mode = goal[5:].strip()
            agent.switch_mode(mode)
            print(f"Switched to {mode}")
            continue
        print(f"Running: {goal}")
        try:
            result = await agent.run_task(goal, mode=args.mode)
            text = result.get("result") or str(result)
            print(f"\nResult:\n{text[:4000]}")
        except Exception as e:
            print(f"Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="AUTOBOT Autonomous Agent")
    parser.add_argument("--goal", help="Run a single goal and exit")
    parser.add_argument("--mode", default="coder", help="Agent mode")
    parser.add_argument("--repl", action="store_true", help="Interactive REPL")
    parser.add_argument("--gateway", default=None, help="Gateway URL (overrides AUTOBOT_GATEWAY_URL)")
    parser.add_argument("--gateway-key", default=None, help="Gateway API key (overrides AUTOBOT_GATEWAY_KEY)")
    args = parser.parse_args()

    # Apply CLI overrides to config (TradingAgents-style env bridge)
    if args.gateway:
        Config().set("gateway_url", args.gateway.rstrip("/"))
    if args.gateway_key:
        Config().set("gateway_key", args.gateway_key)

    workspace = Path(os.getcwd())
    print(f"AUTOBOT starting — workspace: {workspace}")
    agent = AutobotAgent(workspace_root=str(workspace))

    if args.goal:
        print(f"Running goal: {args.goal}")
        result = await agent.run_task(args.goal, mode=args.mode)
        text = result.get("result") or str(result)
        print(f"\nResult:\n{text[:4000]}")
    elif args.repl:
        await repl(agent)
    else:
        print("No goal specified. Use --goal or --repl. See --help.")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
