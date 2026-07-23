
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional


class SubAgentSpawner:
    def __init__(self, memory: Optional[Any] = None) -> None:
        self.memory = memory

    async def spawn(
        self,
        task: str,
        mode: str = "coder",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from autobot.runtime import AgentRuntime
        rt = AgentRuntime.shared()
        memory = self.memory or rt.get_memory()
        try:
            result = await rt.spawn(task, mode=mode)
            memory.add(
                f"Sub-agent ({mode}) completed: {task[:100]}",
                source="subagent",
                metadata={"mode": mode, "context": context, "result": result},
            )
            return {"status": "ok", "mode": mode, "result": result}
        except Exception as exc:
            memory.add(
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
