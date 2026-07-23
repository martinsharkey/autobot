
from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gateway.state import config
from autobot.runtime import AgentRuntime

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/v1/coaching/status")
async def coaching_status():
    rt = AgentRuntime.shared()
    return rt.get_coaching().get_status()


@router.post("/v1/coaching/round")
async def coaching_round(request: Request):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    body = await request.json()
    difficulty = body.get("difficulty", "medium")
    topic = body.get("topic")
    rt = AgentRuntime.shared()
    result = await rt.get_coaching().run_coaching_round(difficulty=difficulty, topic=topic)
    return JSONResponse(content=result)


@router.post("/v1/coaching/target")
async def coaching_target(request: Request):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    body = await request.json()
    target = int(body.get("target", 50))
    rt = AgentRuntime.shared()
    rt.get_coaching().win_target = target
    return JSONResponse(content={"status": "ok", "win_target": target})
