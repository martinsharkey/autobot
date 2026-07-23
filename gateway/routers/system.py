
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from gateway.state import config, provider_health, provider_failure_count

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
async def update_providers(request: Any):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})
    return {"status": "ok", "message": "Provider update handled by discovery"}
