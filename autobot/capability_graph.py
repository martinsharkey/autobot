
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolCapabilityGraph:
    def __init__(self, tool_registry: Any) -> None:
        self._registry = tool_registry
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def probe_all(self) -> Dict[str, Dict[str, Any]]:
        capabilities: Dict[str, Dict[str, Any]] = {}
        try:
            names = self._registry.get_names()
        except Exception:
            names = []

        for name in names:
            capabilities[name] = await self._probe_tool(name)
        self._cache = capabilities
        return capabilities

    async def _probe_tool(self, name: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {"available": False, "reason": "not_probed"}
        try:
            entry = self._registry.get_entry(name)
            if not entry:
                return info
            available = self._registry.is_available(name)
            info["available"] = bool(available)
            info["reason"] = "ok" if available else "unavailable"
        except Exception as exc:
            info["reason"] = f"error:{exc}"
        return info

    def to_prompt_block(self) -> str:
        lines = ["[Tool capabilities]"]
        for name, capability in self._cache.items():
            status = "available" if capability.get("available") else f"unavailable ({capability.get('reason')})"
            lines.append(f"- {name}: {status}")
        return "\n".join(lines)
