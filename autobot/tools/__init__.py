
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from autobot.verification import ToolResultVerifier

_HERMES_DIR = Path(__file__).resolve().parent.parent.parent / "hermes-repo"
if str(_HERMES_DIR) not in sys.path:
    sys.path.append(str(_HERMES_DIR))

from tools.registry import (  # noqa: E402
    registry as _registry,
    discover_builtin_tools,
    ToolEntry,
    ToolRegistry as HermesToolRegistry,
    tool_error,
    tool_result,
    invalidate_check_fn_cache,
)

_verifier = ToolResultVerifier()


class ToolRegistry:
    def __init__(self, auto_discover: bool = True, mcp_bridge: Optional[Any] = None) -> None:
        self._registry = _registry
        self._discovered = False
        self._verifier = _verifier
        self._mcp_bridge = mcp_bridge
        if auto_discover:
            self.discover()

    def discover(self) -> int:
        count = 0
        try:
            discovered = discover_builtin_tools()
            count = len(discovered)
        except Exception as exc:
            print(f"[autobot.tools] discover failed: {exc}")
        try:
            from autobot.tools.self_patch_tools import register_self_patch_tools
            register_self_patch_tools(self._registry)
            count += 2
        except Exception as exc:
            print(f"[autobot.tools] self-patch register failed: {exc}")
        self._discovered = True
        return count

    def ensure_loaded(self) -> None:
        if not self._discovered:
            self.discover()

    def get_definitions(self, toolsets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        self.ensure_loaded()
        try:
            from model_tools import get_tool_definitions
            hermes_defs = get_tool_definitions(required_toolsets=toolsets) or []
        except Exception:
            hermes_defs = []
        mcp_defs = self._get_mcp_tool_definitions()
        return hermes_defs + mcp_defs

    def get_names(self) -> List[str]:
        self.ensure_loaded()
        try:
            from model_tools import get_all_tool_names
            hermes_names = get_all_tool_names() or []
        except Exception:
            hermes_names = []
        mcp_names = [t.get("name", "") for t in self._get_mcp_tool_definitions()]
        return hermes_names + mcp_names

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        return self._registry.get_entry(name)

    def is_available(self, name: str) -> bool:
        self.ensure_loaded()
        try:
            entry = self._registry.get_entry(name)
            if entry is None:
                return False
            if not entry.check_fn:
                return True
            from tools.registry import _check_fn_cached
            return _check_fn_cached(entry.check_fn)
        except Exception:
            return False

    async def call(self, name: str, args: Dict[str, Any], task_id: Optional[str] = None) -> str:
        self.ensure_loaded()
        mcp_result = await self._try_mcp_call(name, args)
        if mcp_result is not None:
            return mcp_result
        try:
            from model_tools import handle_function_call
            result = handle_function_call(name, args, task_id=task_id)
            verification = _verifier.verify(name, args, result)
            if not verification.valid or verification.confidence < 0.5:
                print(f"[autobot.tools] verification issues for {name}: {verification.issues}")
            if verification.citations:
                print(f"[autobot.tools] citations for {name}: {verification.citations}")
            return result
        except Exception as exc:
            return tool_error(f"{name} failed: {exc}")

    def set_mcp_bridge(self, bridge: Optional[Any]) -> None:
        self._mcp_bridge = bridge
        try:
            self._mcp_bridge  # type: ignore[unused-import]
        except Exception:
            pass

    def _get_mcp_tool_definitions(self) -> List[Dict[str, Any]]:
        if not self._mcp_bridge:
            return []
        try:
            bridge = self._mcp_bridge
            if hasattr(bridge, "get_tool_registry_schema"):
                return bridge.get_tool_registry_schema()
            return []
        except Exception:
            return []

    def _try_mcp_call(self, name: str, args: Dict[str, Any]) -> Optional[str]:
        if not self._mcp_bridge:
            return None
        try:
            bridge = self._mcp_bridge
            tools = bridge.get_tool_registry_schema() if hasattr(bridge, "get_tool_registry_schema") else []
            for tool in tools:
                if tool.get("name") == name:
                    server = tool.get("server", "")
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        return None
                    result = loop.run_until_complete(bridge.call_tool(server_name=server, tool_name=name, arguments=args))
                    content = result.get("content", [])
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    return "\n".join(text_parts) or str(result)
        except Exception as exc:
            return tool_error(f"mcp {name} failed: {exc}")
        return None
