
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Dict, Optional, Union

from autobot.agent import AutobotAgent
from autobot.hermes_loop import HermesLoop
from autobot.memory import MemoryStore
from autobot.subagent import SubAgentSpawner
from autobot.tools import ToolRegistry


class AgentRuntime:
    _instance: Optional["AgentRuntime"] = None

    def __init__(self) -> None:
        self._agent = AutobotAgent()
        self._spawner = SubAgentSpawner()
        self._memory = MemoryStore()
        self._tools = ToolRegistry()

    @classmethod
    def shared(cls) -> "AgentRuntime":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def execute(self, goal: str, mode: str = "coder", **kwargs) -> Dict[str, Any]:
        self._memory.add(f"execute: {goal[:100]}", source="runtime", metadata={"mode": mode})
        result = await self._agent.run(goal)
        return {"status": "ok", "mode": mode, "result": result.get("result", "")}

    async def spawn(self, goal: str, mode: str = "coder", **kwargs) -> Dict[str, Any]:
        return await self._spawner.spawn(goal, mode=mode)

    async def batch(self, tasks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return await self._spawner.spawn_batch(tasks)

    def get_memory(self) -> MemoryStore:
        return self._memory

    def get_tools(self) -> ToolRegistry:
        return self._tools

    def switch_mode(self, mode: str) -> None:
        self._agent.switch_mode(mode)
