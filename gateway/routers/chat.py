
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from gateway.state import config
from gateway.state import provider_health, provider_failure_count, active_agents
from autobot.router import _route_providers

router = APIRouter()


def _select_providers():
    items = sorted(
        config.providers,
        key=lambda p: (
            provider_health.get(p.name, 0),
            provider_failure_count.get(p.name, 0),
            -p.weight,
        ),
    )
    available = []
    for p in items:
        if provider_health.get(p.name, 0) > time.time():
            continue
        if p.api_key_env:
            key = os.getenv(p.api_key_env)
            if not key:
                continue
        available.append(p)
    return available


def _build_headers(provider):
    headers = {"Content-Type": "application/json"}
    if provider.api_key_env:
        key = os.getenv(provider.api_key_env)
        if key:
            headers["Authorization"] = f"{provider.api_key_prefix} {key}"
    return headers


def _transform(provider, payload):
    model_name = payload.get("model")
    if model_name == "gateway" and provider.default_model:
        mapped = dict(payload)
        mapped["model"] = provider.default_model
        return mapped
    if provider.model_map and model_name in provider.model_map:
        mapped = dict(payload)
        mapped["model"] = provider.model_map[model_name]
        return mapped
    return payload


async def _forward_chat(payload: Dict[str, Any]) -> JSONResponse:
    providers = _route_providers(payload, _select_providers())
    if not providers:
        return JSONResponse(
            status_code=503,
            content={
                "error": "No healthy providers available",
                "provider_states": [
                    {"name": p.name, "has_api_key": bool(os.getenv(p.api_key_env)) if p.api_key_env else True, "active": p.active}
                    for p in config.providers
                ],
            },
        )
    errors = []
    for provider in providers:
        url = f"{provider.base_url.rstrip('/')}/{provider.completions_path.lstrip('/')}"
        proj_payload = _transform(provider, payload)
        try:
            async with httpx.AsyncClient(timeout=provider.timeout_seconds) as client:
                resp = await client.post(url, headers=_build_headers(provider), json=proj_payload)
            if resp.status_code < 300:
                provider_health.pop(provider.name, None)
                provider_failure_count.pop(provider.name, None)
                try:
                    content = resp.json()
                except Exception:
                    content = {"raw": resp.text[:500]}
                return JSONResponse(status_code=resp.status_code, content=content)
            errors.append({"provider": provider.name, "status_code": resp.status_code, "text": resp.text[:200]})
            provider_failure_count[provider.name] = provider_failure_count.get(provider.name, 0) + 1
            consecutive = provider_failure_count.get(provider.name, 0)
            if consecutive >= 2 and (resp.status_code >= 500 or resp.status_code == 429):
                provider_health[provider.name] = time.time() + min(15 * (2 ** (consecutive - 2)), 300)
        except Exception as exc:
            errors.append({"provider": provider.name, "error": str(exc)})
            provider_failure_count[provider.name] = provider_failure_count.get(provider.name, 0) + 1
            consecutive = provider_failure_count.get(provider.name, 0)
            if consecutive >= 2:
                provider_health[provider.name] = time.time() + min(15 * (2 ** (consecutive - 2)), 300)
    raise HTTPException(status_code=502, detail={"errors": errors})


async def _stream_chat_completions(payload: Dict[str, Any]) -> StreamingResponse:
    providers = _route_providers(payload, _select_providers())
    if not providers:
        raise HTTPException(status_code=503, detail="No healthy providers")

    async def generate():
        for provider in providers:
            url = f"{provider.base_url.rstrip('/')}/{provider.completions_path.lstrip('/')}"
            proj_payload = _transform(provider, payload)
            try:
                async with httpx.AsyncClient(timeout=provider.timeout_seconds) as client:
                    async with client.stream("POST", url, headers=_build_headers(provider), json=proj_payload) as resp:
                        if resp.status_code < 300:
                            ctype = resp.headers.get("content-type", "")
                            if "text/event-stream" in ctype:
                                async for line in resp.aiter_lines():
                                    if line.startswith("data: "):
                                        yield line + "\n\n"
                                return
                            body = await resp.aread()
                            try:
                                data = json.loads(body)
                                choices = data.get("choices") or []
                                finish_reason = choices[0].get("finish_reason") if choices else "stop"
                                message = choices[0].get("message", {}) if choices else {}
                                chunk = {
                                    "id": data.get("id", "gw-stream"),
                                    "object": "chat.completion.chunk",
                                    "created": data.get("created"),
                                    "model": data.get("model"),
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {"content": message.get("content", "")},
                                            "finish_reason": finish_reason,
                                        }
                                    ],
                                }
                                yield f"data: {json.dumps(chunk)}\n\n"
                                yield "data: [DONE]\n\n"
                                return
                            except Exception:
                                yield "data: [DONE]\n\n"
                                return
            except Exception:
                continue
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    if payload.get("stream"):
        return await _stream_chat_completions(payload)
    return await _forward_chat(payload)


@router.post("/v1/chat/stream")
async def chat_stream(request: Request):
    payload = await request.json()
    return await _stream_chat_completions(payload)
