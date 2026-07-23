
from __future__ import annotations

import json
import logging
import os
from typing import Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gateway.state import config, provider_health, provider_failure_count

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/v1/health")
async def health():
    return {"status": "ok", "provider_count": len(config.providers)}


@router.get("/v1/providers")
async def providers_list():
    return {
        "providers": [
            {
                "name": p.name,
                "base_url": p.base_url,
                "active": p.active,
                "weight": p.weight,
                "has_api_key": bool(os.getenv(p.api_key_env)) if p.api_key_env else True,
            }
            for p in config.providers
        ]
    }


@router.get("/v1/discover")
async def discover_endpoint():
    import httpx
    discovered = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://api.github.com/repos/xinrui-z/free-llm/contents/site/src/data/providers")
            if resp.status_code == 200:
                for file in resp.json():
                    if not file["name"].endswith(".json") or file["name"] in ("_order.json", "index.ts"):
                        continue
                    try:
                        cresp = await client.get(file["download_url"])
                        if cresp.status_code == 200:
                            data = cresp.json()
                            pid = data.get("id", "")
                            discovered.append({
                                "name": pid,
                                "base_url": data.get("base_url", ""),
                                "default_model": (data.get("top_models") or [None])[0],
                                "active": data.get("status", "active") == "active",
                            })
                    except Exception:
                        continue
    except Exception:
        pass
    return {"discovered_providers": discovered}


@router.post("/v1/update-providers")
async def update_providers(request: Request):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    return {"status": "ok", "message": "Provider update handled by discovery"}


@router.post("/v1/notifications/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        from autobot.remote_commands import RemoteCommandProtocol
        rc = RemoteCommandProtocol()
        result = rc.handle_telegram_update(update)
        if result is None:
            return JSONResponse(content={"status": "ignored"})
        return JSONResponse(content=result)
    except Exception as exc:
        logger.warning("telegram webhook failed: %s", exc)
        return JSONResponse(status_code=200, content={"status": "error", "error": str(exc)})


@router.post("/v1/notifications/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    try:
        payload = await request.json()
        from autobot.remote_commands import RemoteCommandProtocol
        rc = RemoteCommandProtocol()
        result = rc.handle_whatsapp_message(payload)
        if result is None:
            return JSONResponse(content={"status": "ignored"})
        return JSONResponse(content=result)
    except Exception as exc:
        logger.warning("whatsapp webhook failed: %s", exc)
        return JSONResponse(status_code=200, content={"status": "error", "error": str(exc)})


@router.post("/v1/notifications/send")
async def send_notification(request: Request):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    body = await request.json()
    text = body.get("text", "")
    if not text:
        return JSONResponse(status_code=400, content={"error": "missing text"})
    from autobot.notifications import NotificationClient
    nc = NotificationClient()
    result = nc.notify(text, priority=body.get("priority", "normal"))
    return JSONResponse(content=result)
