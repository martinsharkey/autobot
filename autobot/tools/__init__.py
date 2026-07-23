
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from autobot.verification import ToolResultVerifier

_HERMES_DIR = Path(__file__).resolve().parent.parent.parent / "hermes-repo"
if str(_HERMES_DIR) not in sys.path:
    sys.path.insert(0, str(_HERMES_DIR))

from tools.registry import (  # noqa: E402
    registry as _registry,
    discover_builtin_tools,
    ToolEntry,
    ToolRegistry,
    tool_error,
    tool_result,
    invalidate_check_fn_cache,
)

_verifier = ToolResultVerifier()


class ToolRegistry:
    def __init__(self, auto_discover: bool = True) -> None:
        self._registry = _registry
        self._discovered = False
        if auto_discover:
            self.discover()

    def discover(self) -> int:
        count = 0
        try:
            count = discover_builtin_tools()
        except Exception as exc:
            print(f"[autobot.tools] discover failed: {exc}")
        self._discovered = True
        return count

    def ensure_loaded(self) -> None:
        if not self._discovered:
            self.discover()

    def get_definitions(self, toolsets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        self.ensure_loaded()
        try:
            from model_tools import get_tool_definitions
            return get_tool_definitions(required_toolsets=toolsets) or []
        except Exception:
            return []

    def get_names(self) -> List[str]:
        self.ensure_loaded()
        try:
            from model_tools import get_all_tool_names
            return get_all_tool_names() or []
        except Exception:
            return []

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        return self._registry.get(name)

    def is_available(self, name: str) -> bool:
        self.ensure_loaded()
        try:
            return bool(check_tool_availability(name))
        except Exception:
            return False

    async def call(self, name: str, args: Dict[str, Any], task_id: Optional[str] = None) -> str:
        self.ensure_loaded()
        try:
            result = handle_function_call(name, args, task_id=task_id)
            verification = _verifier.verify(name, args, result)
            if not verification.valid or verification.confidence < 0.5:
                print(f"[autobot.tools] verification issues for {name}: {verification.issues}")
            if verification.citations:
                print(f"[autobot.tools] citations for {name}: {verification.citations}")
            return result
        except Exception as exc:
            return tool_error(f"{name} failed: {exc}")
