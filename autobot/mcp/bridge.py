
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class MCPBridge:
    def __init__(self, server_url: str, api_key: Optional[str] = None) -> None:
        self._server_url = server_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30)

    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self._server_url:
            return []
        try:
            resp = await self._client.get(f"{self._server_url}/tools", headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("tools", [])
        except Exception as exc:
            logger.warning("MCP list_tools failed: %s", exc)
        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._server_url:
            return {"error": "no_mcp_server"}
        try:
            resp = await self._client.post(f"{self._server_url}/tools/call", headers=self._headers(), json={"name": name, "arguments": arguments})
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"mcp_status_{resp.status_code}", "detail": resp.text[:200]}
        except Exception as exc:
            logger.warning("MCP call_tool failed: %s", exc)
            return {"error": str(exc)}

    def close(self) -> None:
        try:
            asyncio.get_event_loop().run_until_complete(self._client.aclose())
        except Exception:
            pass

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
