
from __future__ import annotations

import asyncio
import inspect
import os
from typing import Any, Dict, List, Optional, Union

from autobot.agent import AutobotAgent
from autobot.governance import GovernanceModule, SafetyRails
from autobot.hermes_loop import HermesLoop
from autobot.mcp.bridge import MCPBridge
from autobot.memory import MemoryStore
from autobot.plugins.interface import PluginRegistry
from autobot.subagent import SubAgentSpawner
from autobot.tools import ToolRegistry


class AgentRuntime:
    _instance: Optional["AgentRuntime"] = None

    def __init__(self) -> None:
        self._agent = AutobotAgent()
        self._spawner = SubAgentSpawner()
        self._memory = MemoryStore()
        self._tools = ToolRegistry()
        self._governance = GovernanceModule()
        self._plugins = PluginRegistry()
        self._mcp = MCPBridge(server_url=os.getenv("AUTOBOT_MCP_SERVER", ""), api_key=os.getenv("AUTOBOT_MCP_KEY"))
        try:
            self._plugins.discover()
        except Exception:
            pass

    @classmethod
    def shared(cls) -> "AgentRuntime":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def execute(self, goal: str, mode: str = "coder", **kwargs) -> Dict[str, Any]:
        self._memory.add(f"execute: {goal[:100]}", source="runtime", metadata={"mode": mode})
        if self._governance:
            try:
                self._governance.log_audit("execute", {"goal": goal[:200], "mode": mode})
            except Exception:
                pass
        result = await self._agent.run(goal)
        output = result.get("result", "")
        if self._governance and output:
            try:
                rail = SafetyRails.validate_command(output)
                if not rail.get("allowed", True) and self._looks_like_command(output):
                    output = f"[SAFETY_BLOCKED] {rail.get('reason', '')}"
                    result = {**result, "result": output, "safety_blocked": True}
            except Exception:
                pass
        return {"status": "ok", "mode": mode, "result": result.get("result", "")}

    @staticmethod
    def _looks_like_command(text: str) -> bool:
        stripped = text.strip()
        if stripped.startswith("$") or stripped.startswith(">") or stripped.startswith("#"):
            return True
        lines = stripped.splitlines()
        for line in lines[:3]:
            if any(line.startswith(p) for p in ("sudo ", "rm ", "chmod ", "dd ", "mkfs ", "shutdown ", "reboot ")):
                return True
        return False

    async def spawn(self, goal: str, mode: str = "coder", **kwargs) -> Dict[str, Any]:
        return await self._spawner.spawn(goal, mode=mode)

    async def batch(self, tasks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        return await self._spawner.spawn_batch(tasks)

    def get_memory(self) -> MemoryStore:
        return self._memory

    def get_tools(self) -> ToolRegistry:
        return self._tools

    def get_plugins(self) -> PluginRegistry:
        return self._plugins

    def get_mcp(self) -> MCPBridge:
        return self._mcp

    def switch_mode(self, mode: str) -> None:
        self._agent.switch_mode(mode)
