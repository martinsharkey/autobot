
from __future__ import annotations

import json
from typing import Any, Dict, List


class MCPBridge:
    def __init__(self, server_url: str, api_key: Optional[str] = None) -> None:
        self._server_url = server_url.rstrip("/")
        self._api_key = api_key

    def list_tools(self) -> List[Dict[str, Any]]:
        return []

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "MCP bridge not yet connected"}
