
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from autobot.tools import ToolRegistry
from autobot.memory import MemoryStore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "hermes-repo"))

from providers import ProviderProfile, register_provider
from run_agent import AIAgent


AUTOBOT_GATEWAY = os.getenv("AUTOBOT_GATEWAY", "http://127.0.0.1:8001/v1").rstrip("/")
AUTOBOT_API_KEY = os.getenv("AUTOBOT_API_KEY", "changeme")

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

    async def run(self, goal: str) -> str:
        self.tools.ensure_loaded()
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
                user_message=goal,
                task_id=self._last_task_id,
            )
            final = result.get("final_response") or result.get("response") or ""
            messages = result.get("messages", [])
            self.memory.add(final or goal, source=self.mode, metadata={"message_count": len(messages)})
            return final or str(result)
        finally:
            try:
                agent.close()
            except Exception:
                pass
