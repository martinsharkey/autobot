
from __future__ import annotations

import asyncio
import inspect
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from autobot.agent import AutobotAgent
from autobot.capability_graph import ToolCapabilityGraph
from autobot.compute import publish_result
from autobot.context_sanitizer import sanitize_context_files
from autobot.deploy import prepare_release, validate_release
from autobot.evolution import GapAnalysisEngine
from autobot.governance import GovernanceModule, SafetyRails
from autobot.hermes_loop import HermesLoop
from autobot.mcp.bridge import MCPBridge
from autobot.memory import MemoryStore
from autobot.overnight import OvernightLearner
from autobot.plugins.interface import PluginRegistry
from autobot.safety import SafetyPolicy
from autobot.subagent import SubAgentSpawner
from autobot.tools import ToolRegistry
from autobot.windows_compat import ensure_windows_compat
from autobot.trading.mt5_connector import MT5Connector
from autobot.trading.risk_manager import RiskManager


class AgentRuntime:
    _instance: Optional["AgentRuntime"] = None

    def __init__(self) -> None:
        self._agent = AutobotAgent()
        self._spawner = SubAgentSpawner()
        self._memory = MemoryStore()
        self._mcp = MCPBridge()
        self._tools = ToolRegistry(mcp_bridge=self._mcp)
        self._governance = GovernanceModule()
        self._plugins = PluginRegistry()
        self._evolution = GapAnalysisEngine()
        self._overnight = OvernightLearner()
        self._safety = SafetyPolicy()
        self._mt5 = MT5Connector()
        self._risk = RiskManager()
        from autobot.delegation import HierarchicalDelegator
        self._delegator = HierarchicalDelegator()
        ensure_windows_compat()
        try:
            self._plugins.discover()
        except Exception:
            pass
        try:
            sanitize_context_files(Path(os.getenv("AUTOBOT_HOME", ".")))
        except Exception:
            pass

    @classmethod
    def shared(cls) -> "AgentRuntime":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def execute(self, goal: str, mode: str = "coder", **kwargs) -> Dict[str, Any]:
        if self._safety.is_aborted():
            return {"status": "aborted", "mode": mode, "result": "Safety abort flag is set. Resetting abort."}
        self._memory.add(f"execute: {goal[:100]}", source="runtime", metadata={"mode": mode})
        if self._governance:
            try:
                self._governance.log_audit("execute", {"goal": goal[:200], "mode": mode})
            except Exception:
                pass
        if mode == "evolver":
            try:
                gaps = self._evolution.scan()
                self._memory.add(f"evolution_scan: {len(gaps)} gaps", source="evolution", metadata={"gaps": gaps})
            except Exception:
                pass
        if mode == "trader":
            try:
                account = self._mt5.get_account_info()
                if "error" not in account:
                    risk = self._risk.validate_order({"volume": 0.1}, account)
                    if not risk.get("allowed", False):
                        return {"status": "blocked", "mode": mode, "result": f"Risk blocked: {risk.get('reason')}"}
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

    async def evolve(self) -> Dict[str, Any]:
        gaps = self._evolution.scan()
        release = prepare_release()
        validation = validate_release(release.get("staging"))
        self._memory.add(f"evolve: {len(gaps)} gaps, staging={release.get('staging')}", source="evolution", metadata={"gaps": gaps, "release": release, "validation": validation})
        if validation.get("valid"):
            publish_result("evolution", {"gaps": gaps, "release": release})
            return {"status": "evolved", "gaps": len(gaps), "release": release}
        return {"status": "validation_failed", "validation": validation}

    async def overnight(self) -> Dict[str, Any]:
        if not self._overnight.should_run():
            return {"status": "skipped", "reason": "not_yet_due"}
        result = self._overnight.run_curator()
        self._memory.add("overnight_curator_run", source="overnight", metadata=result)
        return {"status": "ran", "result": result}

    def get_memory(self) -> MemoryStore:
        return self._memory

    def get_tools(self) -> ToolRegistry:
        return self._tools

    def get_plugins(self) -> PluginRegistry:
        return self._plugins

    def get_mcp(self) -> MCPBridge:
        return self._mcp

    def get_safety(self) -> SafetyPolicy:
        return self._safety

    def switch_mode(self, mode: str) -> None:
        self._agent.switch_mode(mode)
