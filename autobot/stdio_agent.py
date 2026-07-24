"""Fused local agent stdio server for VS Code extension.

Reads JSON requests from stdin, executes via direct provider routing,
writes JSON responses to stdout. No gateway HTTP layer.

Protocol:
  Input:  {"id":"...","method":"run","params":{"goal":"...","mode":"coder"}}
  Output: {"id":"...","result":{...}}
"""
from __future__ import annotations

from typing import Callable, Optional

import asyncio
import json
import os
import sys
from pathlib import Path

_AUTOBOT_DIR = Path(__file__).parent
_HERMES_DIR = _AUTOBOT_DIR.parent / "hermes-repo"
_TRADING_DIR = _AUTOBOT_DIR.parent / "trading-repo"

for _p in [str(_HERMES_DIR), str(_TRADING_DIR)]:
    if _p not in sys.path:
        sys.path.append(_p)

env_path = _AUTOBOT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            if key not in os.environ:
                os.environ[key] = value

from autobot.llm import LLMClient
from autobot.memory import MemoryStore
from autobot.tools import ToolRegistry
from autobot.mcp.bridge import MCPBridge
from autobot.safety import SafetyPolicy
from autobot.governance import GovernanceModule
from autobot.trading.mt5_connector import MT5Connector
from autobot.trading.risk_manager import RiskManager
from autobot.subagent import SubAgentSpawner
from autobot.evolution import GapAnalysisEngine
from autobot.overnight import OvernightLearner
from autobot.plugins.interface import PluginRegistry
from autobot.windows_compat import ensure_windows_compat
from autobot.context_sanitizer import sanitize_context_files
from autobot.delegation import HierarchicalDelegator


class FusedAgentServer:
    def __init__(self) -> None:
        self._llm = LLMClient(direct=True)
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

    async def execute(self, goal: str, mode: str = "coder", on_event: Optional[Callable] = None) -> dict:
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

        try:
            from autobot.runtime import AgentRuntime
            rt = AgentRuntime.shared()
            result = await rt.execute(goal, mode=mode, on_event=on_event)
            return result
        except Exception as exc:
            return {"status": "error", "mode": mode, "result": str(exc)}

    async def spawn(self, goal: str, mode: str = "coder") -> dict:
        return await self._spawner.spawn(goal, mode=mode)

    async def evolve(self) -> dict:
        gaps = self._evolution.scan()
        return {"gaps": gaps, "status": "ok"}

    def get_coaching(self) -> dict:
        from autobot.coaching_framework import CoachingFramework
        if not hasattr(self, "_coaching"):
            self._coaching = CoachingFramework()
        return self._coaching.get_status()

    def get_memory(self) -> dict:
        try:
            entries = self._memory.all()
            return {"entries": entries[:100], "total": len(entries)}
        except Exception:
            return {"entries": [], "total": 0}


async def handle_request(server: FusedAgentServer, request: dict) -> dict:
    req_id = request.get("id", "unknown")
    method = request.get("method", "")
    params = request.get("params", {})

    try:
        if method == "run":
            goal = params.get("goal", "")
            mode = params.get("mode", "coder")

            def on_event(event):
                import json
                print(json.dumps({"id": req_id, "event": event}, ensure_ascii=False), flush=True)

            result = await server.execute(goal, mode=mode, on_event=on_event)
            return {"id": req_id, "result": result}
        elif method == "spawn":
            goal = params.get("goal", "")
            mode = params.get("mode", "coder")
            result = await server.spawn(goal, mode=mode)
            return {"id": req_id, "result": result}
        elif method == "evolve":
            result = await server.evolve()
            return {"id": req_id, "result": result}
        elif method == "coaching":
            result = server.get_coaching()
            return {"id": req_id, "result": result}
        elif method == "memory":
            result = server.get_memory()
            return {"id": req_id, "result": result}
        elif method == "health":
            return {"id": req_id, "result": {"status": "ok", "mode": "fused"}}
        else:
            return {"id": req_id, "error": f"unknown method: {method}"}
    except Exception as exc:
        return {"id": req_id, "error": str(exc)}


async def stdio_loop() -> None:
    server = FusedAgentServer()
    print(json.dumps({"id": "init", "result": {"status": "ok", "mode": "fused"}}), flush=True)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            request = json.loads(line)
            response = await handle_request(server, request)
            print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError as exc:
            print(json.dumps({"id": "unknown", "error": f"invalid json: {exc}"}), flush=True)
        except Exception as exc:
            print(json.dumps({"id": "unknown", "error": str(exc)}), flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(stdio_loop())
    except Exception as exc:
        print(json.dumps({"id": "fatal", "error": str(exc)}), flush=True)
        sys.exit(1)
