import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    api_key_env: Optional[str] = None
    api_key_prefix: str = "Bearer"
    completions_path: str = "chat/completions"
    active: bool = True
    weight: int = 1
    timeout_seconds: int = 20
    model_map: Optional[Dict[str, str]] = None
    default_model: Optional[str] = None


class GatewayConfig(BaseModel):
    gateway_api_key: Optional[str] = None
    providers: List[ProviderConfig] = Field(default_factory=list)


def load_config() -> GatewayConfig:
    config_path = os.path.join(os.path.dirname(__file__), "providers.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Missing provider config: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    gateway_api_key = os.getenv("GATEWAY_API_KEY")
    providers = [ProviderConfig(**item) for item in raw.get("providers", []) if item.get("active", True)]
    return GatewayConfig(gateway_api_key=gateway_api_key, providers=providers)


config = load_config()
app = FastAPI(title="LLM Gateway", version="1.0")

provider_health: Dict[str, float] = {}
provider_failure_count: Dict[str, int] = {}


def select_providers() -> List[ProviderConfig]:
    items = sorted(
        config.providers,
        key=lambda p: (
            provider_health.get(p.name, 0),
            provider_failure_count.get(p.name, 0),
            -p.weight,
        ),
    )
    available = []
    for provider in items:
        if provider_health.get(provider.name, 0) > time.time():
            continue
        # Skip providers that require an API key but don't have one set
        if provider.api_key_env:
            key = os.getenv(provider.api_key_env)
            if not key:
                continue
        available.append(provider)
    return available


def build_headers(provider: ProviderConfig) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if provider.api_key_env:
        api_key = os.getenv(provider.api_key_env)
        if api_key:
            headers["Authorization"] = f"{provider.api_key_prefix} {api_key}"
    return headers


def transform_payload(provider: ProviderConfig, payload: Dict[str, Any]) -> Dict[str, Any]:
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


@app.middleware("http")
async def require_gateway_key(request: Request, call_next):
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        expected = f"Bearer {config.gateway_api_key}"
        if auth != expected:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Missing or invalid gateway API key",
                    "hint": f"Use Authorization: Bearer {config.gateway_api_key}",
                },
            )
    return await call_next(request)


@app.get("/v1/health")
async def health() -> Dict[str, Any]:
    alive = [provider.name for provider in select_providers()]
    provider_states = []
    for provider in config.providers:
        provider_states.append({
            "name": provider.name,
            "active": provider.active,
            "has_api_key": bool(os.getenv(provider.api_key_env)) if provider.api_key_env else True,
            "healthy": provider.name in alive,
        })
    return {
        "status": "ok",
        "provider_count": len(config.providers),
        "provider_states": provider_states,
    }


@app.get("/v1/providers")
async def providers_list() -> Dict[str, Any]:
    return {
        "providers": [
            {
                "name": provider.name,
                "base_url": provider.base_url,
                "active": provider.active,
                "weight": provider.weight,
                "has_api_key": bool(os.getenv(provider.api_key_env)) if provider.api_key_env else True,
            }
            for provider in config.providers
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()

    providers = select_providers()
    if not providers:
        return JSONResponse(
            status_code=503,
            content={
                "error": "No healthy providers available",
                "detail": "Check that your provider API keys are set in .env and that at least one provider is healthy.",
                "provider_states": [
                    {
                        "name": provider.name,
                        "has_api_key": bool(os.getenv(provider.api_key_env)) if provider.api_key_env else True,
                        "active": provider.active,
                    }
                    for provider in config.providers
                ],
            },
        )

    errors: List[Dict[str, Any]] = []
    last_status = None

    for provider in providers:
        provider_url = f"{provider.base_url.rstrip('/')}/{provider.completions_path.lstrip('/')}"
        provider_payload = transform_payload(provider, payload)

        try:
            async with httpx.AsyncClient(timeout=provider.timeout_seconds) as client:
                response = await client.post(
                    provider_url,
                    headers=build_headers(provider),
                    json=provider_payload,
                )
            if response.status_code < 300:
                provider_health.pop(provider.name, None)
                provider_failure_count.pop(provider.name, None)
                return JSONResponse(status_code=response.status_code, content=response.json())

            errors.append({
                "provider": provider.name,
                "status_code": response.status_code,
                "text": response.text,
            })
            last_status = response.status_code
            if response.status_code >= 500 or response.status_code == 429:
                provider_health[provider.name] = time.time() + 15
                provider_failure_count[provider.name] = provider_failure_count.get(provider.name, 0) + 1
        except Exception as exc:
            errors.append({"provider": provider.name, "error": str(exc)})
            provider_health[provider.name] = time.time() + 15
            provider_failure_count[provider.name] = provider_failure_count.get(provider.name, 0) + 1

    raise HTTPException(status_code=502, detail={"errors": errors, "last_status": last_status})


# ══════════════════════════════════════════════════════════════════════════════
# Free LLM Provider Discovery — scans GitHub repos to keep provider list fresh
# ══════════════════════════════════════════════════════════════════════════════

KNOWN_FREE_BASES = {
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "completions_path": "chat/completions", "api_key_env": "OPENROUTER_API_KEY"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "completions_path": "chat/completions", "api_key_env": "GROQ_API_KEY"},
    "cerebras": {"base_url": "https://api.cerebras.ai/v1", "completions_path": "chat/completions", "api_key_env": "CEREBRAS_API_KEY"},
    "mistral": {"base_url": "https://api.mistral.ai/v1", "completions_path": "chat/completions", "api_key_env": "MISTRAL_API_KEY"},
    "deepinfra": {"base_url": "https://api.deepinfra.com/v1/openai", "completions_path": "chat/completions", "api_key_env": "DEEPINFRA_API_KEY"},
    "togetherai": {"base_url": "https://api.together.xyz/v1", "completions_path": "chat/completions", "api_key_env": "TOGETHER_API_KEY"},
    "github-models": {"base_url": "https://models.inference.ai.azure.com", "completions_path": "chat/completions", "api_key_env": "GITHUB_TOKEN"},
    "google-ai-studio": {"base_url": "https://generativelanguage.googleapis.com/v1beta", "completions_path": "models/gemini-2.0-flash:generateContent", "api_key_env": "GEMINI_API_KEY"},
    "huggingface": {"base_url": "https://api-inference.huggingface.co", "completions_path": "models/meta-llama/Meta-Llama-3.1-8B-Instruct/v1/chat/completions", "api_key_env": "HF_API_KEY"},
    "sambanova": {"base_url": "https://api.sambanova.ai/v1", "completions_path": "chat/completions", "api_key_env": "SAMBANOVA_API_KEY"},
    "siliconflow": {"base_url": "https://api.siliconflow.cn/v1", "completions_path": "chat/completions", "api_key_env": "SILICONFLOW_API_KEY"},
    "nvidia-nim": {"base_url": "https://integrate.api.nvidia.com/v1", "completions_path": "chat/completions", "api_key_env": "NVIDIA_API_KEY"},
    "cohere": {"base_url": "https://api.cohere.ai/v1", "completions_path": "chat/completions", "api_key_env": "COHERE_API_KEY"},
    "modelscope": {"base_url": "https://api.modelscope.cn/v1", "completions_path": "chat/completions", "api_key_env": "MODELSCOPE_API_KEY"},
    "aihubmix": {"base_url": "https://aihubmix.com/v1", "completions_path": "chat/completions", "api_key_env": "AIHUBMIX_API_KEY"},
}


async def discover_free_providers_from_github() -> List[Dict[str, Any]]:
    """Scrape the free-llm repo's provider JSON files and return discovered providers."""
    discovered = []
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                "https://api.github.com/repos/xinrui-z/free-llm/contents/site/src/data/providers",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code != 200:
                return discovered
            files = resp.json()
            for file in files:
                if not file["name"].endswith(".json") or file["name"] in ("_order.json", "index.ts"):
                    continue
                try:
                    cresp = await client.get(file["download_url"])
                    if cresp.status_code != 200:
                        continue
                    data = cresp.json()
                    pid = data.get("id", "")
                    if not pid:
                        continue
                    base = KNOWN_FREE_BASES.get(pid, {})
                    discovered.append({
                        "name": pid,
                        "base_url": data.get("base_url", base.get("base_url", "")),
                        "completions_path": base.get("completions_path", "chat/completions"),
                        "api_key_env": data.get("api_key_env", base.get("api_key_env", "")),
                        "default_model": (data.get("top_models") or [None])[0],
                        "free": True,
                        "no_key_required": data.get("auth", "required") in ("optional", "none"),
                        "active": data.get("status", "active") == "active",
                        "weight": 5,
                    })
                except Exception:
                    continue
        except Exception:
            pass
    return discovered


@app.get("/v1/discover")
async def discover_endpoint():
    """Scan GitHub and OpenRouter for free LLM providers / models."""
    gh = await discover_free_providers_from_github()
    # Also check OpenRouter's live model list for free (zero-priced) models
    or_free = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models")
            if resp.status_code == 200:
                for m in resp.json().get("data", []):
                    p = m.get("pricing", {})
                    if float(p.get("prompt", 999)) == 0 and float(p.get("completion", 999)) == 0:
                        or_free.append({"id": m["id"], "name": m.get("name", m["id"]), "context": m.get("context_length", 0)})
    except Exception:
        pass
    return {
        "discovered_providers": gh,
        "openrouter_free_models": or_free,
        "total_free_providers": len(gh),
        "total_free_models_on_openrouter": len(or_free),
        "hint": "POST /v1/update-providers to add all discovered providers to your config",
    }


@app.post("/v1/update-providers")
async def update_providers(request: Request):
    """Auto-discover and append new free providers to providers.yaml."""
    if config.gateway_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {config.gateway_api_key}":
            return JSONResponse(status_code=401, content={"error": "Invalid gateway API key"})

    discovered = await discover_free_providers_from_github()
    cfg_path = os.path.join(os.path.dirname(__file__), "providers.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    existing = {p.get("name") for p in raw.get("providers", [])}
    new_ones = [p for p in discovered if p["name"] not in existing]

    if not new_ones:
        return {"status": "ok", "message": "No new providers found", "added": 0}

    for p in new_ones:
        entry = {"name": p["name"], "base_url": p["base_url"], "completions_path": p["completions_path"], "active": True, "weight": p["weight"]}
        if p.get("api_key_env"):
            entry["api_key_env"] = p["api_key_env"]
        if p.get("default_model"):
            entry["default_model"] = p["default_model"]
        raw.setdefault("providers", []).append(entry)

    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, default_flow_style=False)

        new_cfg = load_config()
    config.providers.clear()
    config.providers.extend(new_cfg.providers)

    return {"status": "ok", "new_providers_added": len(new_ones), "providers": [p["name"] for p in new_ones], "total_providers": len(config.providers)}
