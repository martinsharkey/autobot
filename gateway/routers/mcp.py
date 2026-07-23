
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gateway.state import config
from autobot.runtime import AgentRuntime

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/v1/mcp/servers")
async def list_mcp_servers():
    rt = AgentRuntime.shared()
    return {"servers": rt.get_mcp().list_servers()}


@router.post("/v1/mcp/servers")
async def add_mcp_server(request: Request):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    body = await request.json()
    from autobot.mcp.bridge import MCPServerConfig
    server = MCPServerConfig(
        name=body.get("name", ""),
        transport=body.get("transport", "stdio"),
        command=body.get("command", ""),
        args=body.get("args", []),
        url=body.get("url", ""),
        env=body.get("env", {}),
    )
    rt = AgentRuntime.shared()
    result = rt.get_mcp().add_server(server)
    return JSONResponse(content=result)


@router.delete("/v1/mcp/servers/{name}")
async def remove_mcp_server(name: str, request: Request):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    rt = AgentRuntime.shared()
    result = rt.get_mcp().remove_server(name)
    return JSONResponse(content=result)


@router.post("/v1/mcp/servers/{name}/connect")
async def connect_mcp_server(name: str):
    rt = AgentRuntime.shared()
    result = await rt.get_mcp().connect(name)
    return JSONResponse(content=result)


@router.post("/v1/mcp/servers/{name}/disconnect")
async def disconnect_mcp_server(name: str):
    rt = AgentRuntime.shared()
    result = await rt.get_mcp().disconnect(name)
    return JSONResponse(content=result)


@router.get("/v1/mcp/tools")
async def list_mcp_tools():
    rt = AgentRuntime.shared()
    tools = await rt.get_mcp().list_tools()
    return {"tools": tools}


@router.post("/v1/mcp/tools/call")
async def call_mcp_tool(request: Request):
    body = await request.json()
    server = body.get("server", "")
    tool = body.get("tool", "")
    arguments = body.get("arguments", {})
    rt = AgentRuntime.shared()
    result = await rt.get_mcp().call_tool(server_name=server, tool_name=tool, arguments=arguments)
    return JSONResponse(content=result)
