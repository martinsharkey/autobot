
from __future__ import annotations

from typing import Any, Dict, List, Optional

from autobot.hermes_loop import HermesLoop
from autobot.memory import MemoryStore
from autobot.tools import ToolRegistry
from autobot.llm import LLMClient


class AutobotAgent:
    def __init__(
        self,
        mode: str = "coder",
        llm: Optional[LLMClient] = None,
        memory: Optional[MemoryStore] = None,
        tools: Optional[ToolRegistry] = None,
        memory_store: Optional[MemoryStore] = None,
        workspace_root: Optional[str] = None,
    ) -> None:
        self.mode = mode
        self.llm = llm or LLMClient()
        self.memory = memory or memory_store or MemoryStore()
        self.tools = tools or ToolRegistry()
        self.workspace_root = workspace_root
        self.loop = HermesLoop(memory=self.memory, llm=self.llm, tools=self.tools, mode=mode)
        self.last_result: Optional[str] = None

    async def run(self, goal: str) -> Dict[str, Any]:
        self.last_result = await self.loop.run(goal)
        return {"status": "ok", "result": self.last_result, "mode": self.mode}

    async def run_task(self, goal: str, mode: Optional[str] = None, on_event=None) -> Dict[str, Any]:
        if mode:
            self.mode = mode
        result = await self.run(goal)
        if on_event and result.get("result"):
            on_event({"type": "completed", "text": result["result"]})
        return result

    def switch_mode(self, mode: str) -> None:
        self.mode = mode
        self.loop = HermesLoop(memory=self.memory, llm=self.llm, tools=self.tools, mode=mode)

    async def close(self) -> None:
        await self.llm.close()
