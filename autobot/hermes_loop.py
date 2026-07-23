
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from autobot.tools import ToolRegistry
from autobot.memory import MemoryStore
from autobot.verification import ToolResultVerifier

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "hermes-repo"))

from providers import ProviderProfile, register_provider
from run_agent import AIAgent


AUTOBOT_GATEWAY = os.getenv("AUTOBOT_GATEWAY", "http://127.0.0.1:8001/v1").rstrip("/")
AUTOBOT_API_KEY = os.getenv("AUTOBOT_API_KEY", "changeme")

logger = logging.getLogger(__name__)

try:
    _custom_profile = ProviderProfile(
        name="autobot-gateway",
        api_mode="chat_completions",
        base_url=AUTOBOT_GATEWAY,
        env_vars=("AUTOBOT_API_KEY",),
    )
    register_provider(_custom_profile)
except Exception:
    pass


class HermesLoop:
    def __init__(
        self,
        memory: MemoryStore,
        llm: "LLMClient",
        tools: ToolRegistry,
        mode: str = "coder",
    ) -> None:
        self.memory = memory
        self.llm = llm
        self.tools = tools
        self.mode = mode
        self._last_task_id: Optional[str] = None
        self._verifier = ToolResultVerifier()

    async def run(self, goal: str) -> str:
        self.tools.ensure_loaded()
        citation_goal = goal
        if any(keyword in goal.lower() for keyword in ["search", "find", "look up", "research", "url", "http", "citation"]):
            citation_goal = f"{goal}\n\nIMPORTANT: Always include source citations (URLs or file paths) in your final response. If you use web search or file reading tools, reference the sources you used."
        agent = AIAgent(
            base_url=AUTOBOT_GATEWAY,
            api_key=AUTOBOT_API_KEY,
            provider="autobot-gateway",
            api_mode="chat_completions",
            model="gateway",
            platform="autobot",
            max_iterations=50,
            skip_memory=True,
        )
        try:
            result = await asyncio.to_thread(
                agent.run_conversation,
                user_message=citation_goal,
                task_id=self._last_task_id,
            )
            final = result.get("final_response") or result.get("response") or ""
            messages = result.get("messages", [])
            tool_calls = sum(1 for msg in messages if msg.get("tool_calls"))
            avg_confidence = 0.0
            if tool_calls > 0:
                try:
                    verified = sum(1 for msg in messages if msg.get("tool_calls") and self._verifier.verify("tool_call", {}, msg.get("content", "")).confidence > 0.5)
                    avg_confidence = verified / tool_calls if tool_calls else 0.0
                except Exception:
                    avg_confidence = 0.0
            citation_count = 0
            if any(keyword in goal.lower() for keyword in ["search", "find", "look up", "research", "url", "http", "citation"]):
                try:
                    import re
                    urls = re.findall(r'https?://[^\s)>\]"\']+', final)
                    citation_count = len(urls)
                except Exception:
                    citation_count = 0
            self.memory.add(final or goal, source=self.mode, metadata={"message_count": len(messages), "avg_confidence": avg_confidence, "tool_calls": tool_calls, "citation_count": citation_count})
            return final or str(result)
        finally:
            try:
                agent.close()
            except Exception:
                pass
