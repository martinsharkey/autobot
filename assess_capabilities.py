"""Capability assessment for Autobot."""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load .env
env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            if key not in os.environ:
                os.environ[key] = value

import httpx
from autobot.llm import LLMClient
from autobot.coaching_framework import CoachingFramework
from autobot.runtime import AgentRuntime


async def assess_gateway_chat() -> dict:
    client = LLMClient()
    start = time.time()
    try:
        result = await client.chat("Say hello in 1 word", system="You are a helpful assistant.", temperature=0.1)
        elapsed = time.time() - start
        return {
            "test": "gateway_chat",
            "status": "pass" if result.get("text") else "fail",
            "elapsed_seconds": round(elapsed, 2),
            "response": result.get("text", "")[:100],
            "model": result.get("model"),
        }
    except Exception as exc:
        return {
            "test": "gateway_chat",
            "status": "fail",
            "error": str(exc),
            "elapsed_seconds": round(time.time() - start, 2),
        }


async def assess_agent_run() -> dict:
    rt = AgentRuntime.shared()
    start = time.time()
    try:
        result = await asyncio.wait_for(rt.execute("Write a Python function that returns the sum of two numbers.", mode="coder"), timeout=90)
        elapsed = time.time() - start
        text = result.get("result", "")
        return {
            "test": "agent_run",
            "status": "pass" if text else "fail",
            "elapsed_seconds": round(elapsed, 2),
            "response": text[:200],
        }
    except asyncio.TimeoutError:
        return {
            "test": "agent_run",
            "status": "timeout",
            "elapsed_seconds": round(time.time() - start, 2),
        }
    except Exception as exc:
        return {
            "test": "agent_run",
            "status": "fail",
            "error": str(exc),
            "elapsed_seconds": round(time.time() - start, 2),
        }


async def assess_coaching_round() -> dict:
    fw = CoachingFramework()
    start = time.time()
    try:
        result = await asyncio.wait_for(fw.run_coaching_round(difficulty="easy", topic="python"), timeout=90)
        elapsed = time.time() - start
        return {
            "test": "coaching_round",
            "status": "pass",
            "elapsed_seconds": round(elapsed, 2),
            "winner": result.get("round", {}).get("winner"),
            "streak": result.get("win_streak"),
            "challenge": result.get("challenge", "")[:120],
            "autobot_response": result.get("autobot_response", "")[:120],
            "mentor_response": result.get("mentor_response", "")[:120],
        }
    except asyncio.TimeoutError:
        return {
            "test": "coaching_round",
            "status": "timeout",
            "elapsed_seconds": round(time.time() - start, 2),
        }
    except Exception as exc:
        return {
            "test": "coaching_round",
            "status": "fail",
            "error": str(exc),
            "elapsed_seconds": round(time.time() - start, 2),
        }


async def assess_hermes_agent() -> dict:
    start = time.time()
    try:
        _HERMES_DIR = Path(__file__).resolve().parent / "hermes-repo"
        if str(_HERMES_DIR) not in sys.path:
            sys.path.append(str(_HERMES_DIR))
        from run_agent import AIAgent
        agent = AIAgent(
            base_url="http://127.0.0.1:8001/v1",
            api_key="changeme",
            api_mode="chat_completions",
            model="",
            max_iterations=10,
            enabled_toolsets=["terminal", "file", "search", "code_execution"],
            quiet_mode=True,
        )
        text = agent.run_conversation("Say hello in 1 word")
        elapsed = time.time() - start
        if isinstance(text, dict):
            text = text.get("final_response") or text.get("response") or str(text)
        return {
            "test": "hermes_agent",
            "status": "pass",
            "elapsed_seconds": round(elapsed, 2),
            "response": (text or "")[:120],
        }
    except Exception as exc:
        return {
            "test": "hermes_agent",
            "status": "fail",
            "error": str(exc),
            "elapsed_seconds": round(time.time() - start, 2),
        }


async def main() -> None:
    print("=" * 80)
    print("AUTOBOT CAPABILITY ASSESSMENT")
    print("=" * 80)
    results = []

    print("\n[1/4] Gateway chat...")
    results.append(await assess_gateway_chat())

    print("\n[2/4] Agent runtime...")
    results.append(await assess_agent_run())

    print("\n[3/4] Coaching round...")
    results.append(await assess_coaching_round())

    print("\n[4/4] Hermes agent...")
    results.append(await assess_hermes_agent())

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    for r in results:
        status = r.get("status")
        elapsed = r.get("elapsed_seconds")
        print(f"\n{r['test']}: {status} ({elapsed}s)")
        for k, v in r.items():
            if k in ("test", "status", "elapsed_seconds"):
                continue
            print(f"  {k}: {v}")

    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    timed_out = sum(1 for r in results if r.get("status") == "timeout")
    print(f"\nSUMMARY: passed={passed} failed={failed} timed_out={timed_out} total={len(results)}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
