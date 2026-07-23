
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from autobot.runtime import AgentRuntime

logger = logging.getLogger(__name__)


class TaskNode:
    def __init__(self, node_id: str, goal: str, deps: Optional[List[str]] = None, resources: Optional[Dict[str, Any]] = None) -> None:
        self.node_id = node_id
        self.goal = goal
        self.deps = deps or []
        self.resources = resources or {}
        self.result: Optional[Dict[str, Any]] = None
        self.status: str = "pending"


class HierarchicalDelegator:
    def __init__(self, max_depth: int = 2) -> None:
        self._max_depth = max_depth
        self._runtime = AgentRuntime.shared()

    async def execute_dag(self, nodes: List[TaskNode]) -> Dict[str, Any]:
        by_id = {node.node_id: node for node in nodes}
        completed: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            if not node.deps or all(dep in completed for dep in node.deps):
                node.status = "running"
                try:
                    result = await self._runtime.execute(node.goal, mode="coder")
                    node.result = result
                    node.status = "completed"
                    completed[node.node_id] = result
                except Exception as exc:
                    node.status = "failed"
                    node.result = {"error": str(exc)}
        return {"completed": completed, "nodes": {n.node_id: {"status": n.status, "goal": n.goal} for n in nodes}}
