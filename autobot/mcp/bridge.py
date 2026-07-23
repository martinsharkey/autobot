
from __future__ import annotations

import asyncio
import json
import logging
import shutil
from typing import Any, Dict, List, Optional, Union

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class MCPServerConfig:
    def __init__(self, name: str, transport: str, command: str = "", args: Optional[List[str]] = None, url: str = "", env: Optional[Dict[str, str]] = None) -> None:
        self.name = name
        self.transport = transport
        self.command = command
        self.args = args or []
        self.url = url
        self.env = env or {}
        self._session: Optional[ClientSession] = None
        self._tools_cache: List[Dict[str, Any]] = []


class MCPBridge:
    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerConfig] = {}
        self._sessions: Dict[str, ClientSession] = {}

    def add_server(self, config: MCPServerConfig) -> Dict[str, Any]:
        self._servers[config.name] = config
        return {"status": "added", "server": config.name, "transport": config.transport}

    def remove_server(self, name: str) -> Dict[str, Any]:
        self._close_session(name)
        self._servers.pop(name, None)
        return {"status": "removed", "server": name}

    def list_servers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name,
                "transport": s.transport,
                "command": s.command,
                "url": s.url,
                "tool_count": len(s._tools_cache),
            }
            for s in self._servers.values()
        ]

    async def connect(self, name: str) -> Dict[str, Any]:
        config = self._servers.get(name)
        if not config:
            return {"error": f"server_not_found:{name}"}
        try:
            await self._create_session(config)
            tools = await self._list_tools(name)
            config._tools_cache = tools
            return {"status": "connected", "server": name, "tools": len(tools)}
        except Exception as exc:
            logger.warning("MCP connect failed for %s: %s", name, exc)
            return {"status": "failed", "server": name, "error": str(exc)}

    async def disconnect(self, name: str) -> Dict[str, Any]:
        self._close_session(name)
        return {"status": "disconnected", "server": name}

    async def list_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if server_name:
            config = self._servers.get(server_name)
            if not config:
                return []
            if not config._tools_cache:
                try:
                    config._tools_cache = await self._list_tools(server_name)
                except Exception:
                    pass
            return config._tools_cache
        all_tools: List[Dict[str, Any]] = []
        for name in self._servers:
            try:
                tools = await self.list_tools(name)
                for tool in tools:
                    tool["server"] = name
                all_tools.extend(tools)
            except Exception:
                pass
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        config = self._servers.get(server_name)
        if not config:
            return {"error": f"server_not_found:{server_name}"}
        try:
            session = await self._get_session(server_name)
            if session is None:
                return {"error": "no_session", "server": server_name}
            resp = await session.call_tool(tool_name, arguments)
            content = []
            for item in resp.content or []:
                if hasattr(item, "text"):
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                    content.append({"type": item.type, "data": item.data})
            return {"server": server_name, "tool": tool_name, "content": content}
        except Exception as exc:
            logger.warning("MCP call_tool failed for %s.%s: %s", server_name, tool_name, exc)
            return {"error": str(exc), "server": server_name, "tool": tool_name}

    def get_tool_registry_schema(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for name, config in self._servers.items():
            for tool in config._tools_cache:
                schema = dict(tool)
                schema.setdefault("server", name)
                result.append(schema)
        return result

    async def _create_session(self, config: MCPServerConfig) -> None:
        if config.transport == "stdio":
            if not config.command:
                raise ValueError("stdio transport requires command")
            params = StdioServerParameters(command=config.command, args=config.args, env=config.env)
            read, write = await stdio_client(params).__aenter__()
            session = ClientSession(read, write)
            await session.initialize()
            self._sessions[config.name] = session
        elif config.transport == "sse":
            if not config.url:
                raise ValueError("sse transport requires url")
            read, write = await sse_client(config.url).__aenter__()
            session = ClientSession(read, write)
            await session.initialize()
            self._sessions[config.name] = session
        elif config.transport == "http":
            if not config.url:
                raise ValueError("http transport requires url")
            read, write = await streamablehttp_client(config.url).__aenter__()
            session = ClientSession(read, write)
            await session.initialize()
            self._sessions[config.name] = session
        else:
            raise ValueError(f"unsupported transport:{config.transport}")

    async def _get_session(self, name: str) -> Optional[ClientSession]:
        if name not in self._sessions:
            config = self._servers.get(name)
            if config:
                try:
                    await self._create_session(config)
                except Exception as exc:
                    logger.warning("MCP session creation failed for %s: %s", name, exc)
                    return None
        return self._sessions.get(name)

    async def _list_tools(self, name: str) -> List[Dict[str, Any]]:
        session = await self._get_session(name)
        if session is None:
            return []
        try:
            resp = await session.list_tools()
            tools = []
            for t in (resp.tools or []):
                tools.append({
                    "name": t.name,
                    "description": t.description or "",
                    "input_schema": t.inputSchema or {},
                })
            return tools
        except Exception as exc:
            logger.warning("MCP list_tools failed for %s: %s", name, exc)
            return []

    def _close_session(self, name: str) -> None:
        session = self._sessions.pop(name, None)
        if session is None:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(session.close())
            else:
                loop.run_until_complete(session.close())
        except Exception:
            pass

    async def close(self) -> None:
        for name in list(self._sessions.keys()):
            self._close_session(name)
