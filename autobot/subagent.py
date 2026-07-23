
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from autobot.runtime import AgentRuntime


class SubAgentSpawner:
    def __init__(self, memory: Optional[MemoryStore] = None) -> None:
        self.memory = memory or AgentRuntime.shared().get_memory()

    async def spawn(
        self,
        task: str,
        mode: str = "coder",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        rt = AgentRuntime.shared()
        try:
            result = await rt.spawn(task, mode=mode)
            self.memory.add(
                f"Sub-agent ({mode}) completed: {task[:100]}",
                source="subagent",
                metadata={"mode": mode, "context": context, "result": result},
            )
            return {"status": "ok", "mode": mode, "result": result}
        except Exception as exc:
            self.memory.add(
                f"Sub-agent ({mode}) failed: {task[:100]} — {exc}",
                source="subagent",
                metadata={"mode": mode, "context": context, "error": str(exc)},
            )
            return {"status": "error", "mode": mode, "error": str(exc)}

    async def spawn_batch(self, tasks: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        results = []
        for task in tasks:
            results.append(await self.spawn(task["task"], mode=task.get("mode", "coder"), context=task.get("context")))
        return results
