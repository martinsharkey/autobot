
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
import yaml

from autobot.config import get_mode_config

logger = logging.getLogger(__name__)

AUTOBOT_GATEWAY = os.getenv("AUTOBOT_GATEWAY", "http://127.0.0.1:8001").rstrip("/")
AUTOBOT_API_KEY = os.getenv("AUTOBOT_API_KEY", "changeme")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROVIDERS_PATH = _PROJECT_ROOT / "providers.yaml"
_PROVIDER_HEALTH: Dict[str, float] = {}
_PROVIDER_FAILURES: Dict[str, int] = {}


def _load_env() -> None:
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key not in os.environ:
                os.environ[key] = value


_load_env()


def _load_providers() -> List[Dict[str, Any]]:
    if not _PROVIDERS_PATH.exists():
        return []
    try:
        with open(_PROVIDERS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return [p for p in data.get("providers", []) if p.get("active", True)]
    except Exception as exc:
        logger.debug("failed to load providers.yaml: %s", exc)
        return []


def _provider_api_key(provider: Dict[str, Any]) -> Optional[str]:
    env_name = provider.get("api_key_env")
    if not env_name:
        return None
    return os.getenv(env_name)


def _ranked_providers(difficulty: str = "medium") -> List[Dict[str, Any]]:
    providers = _load_providers()
    now = time.time()

    def rank(p: Dict[str, Any]) -> Tuple[float, int, int]:
        health = _PROVIDER_HEALTH.get(p["name"], 0)
        if health > now:
            return (1, _PROVIDER_FAILURES.get(p["name"], 0), -p.get("weight", 0))
        return (0, _PROVIDER_FAILURES.get(p["name"], 0), -p.get("weight", 0))

    providers.sort(key=rank)
    return providers


def _mark_provider_success(name: str) -> None:
    _PROVIDER_HEALTH.pop(name, None)
    _PROVIDER_FAILURES.pop(name, None)


def _mark_provider_failure(name: str) -> None:
    _PROVIDER_FAILURES[name] = _PROVIDER_FAILURES.get(name, 0) + 1
    consecutive = _PROVIDER_FAILURES[name]
    if consecutive >= 2:
        _PROVIDER_HEALTH[name] = time.time() + min(15 * (2 ** (consecutive - 2)), 300)


def _autofree_rank(p: Dict[str, Any]) -> int:
    model = (p.get("default_model") or "").lower()
    name = p.get("name", "").lower()
    score = 0
    if "free" in model:
        score += 10
    if any(token in model for token in ["llama-3.1-8b", "llama-3.3-8b", "gemini-2.0-flash", "gemini-2.5-flash", "glm-4.7-flash"]):
        score += 5
    if any(token in name for token in ["openrouter", "groq", "huggingface", "aihubmix", "deepseek"]):
        score += 3
    return -score


class LLMClient:
    def __init__(
        self,
        gateway_url: str = AUTOBOT_GATEWAY,
        api_key: str = AUTOBOT_API_KEY,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        direct: bool = False,
    ) -> None:
        gateway_url = gateway_url.rstrip("/")
        if gateway_url.endswith("/v1"):
            gateway_url = gateway_url[:-3]
        self._gateway_url = gateway_url.rstrip("/")
        self._api_key = api_key
        self._provider_name = provider_name
        self._model = model
        self._direct = direct
        self._client = httpx.AsyncClient(timeout=120)

    async def chat_completions(
        self,
        payload: Dict[str, Any],
        retries: int = 3,
        backoff: float = 2.0,
        prefer_direct: bool = False,
    ) -> Dict[str, Any]:
        if self._direct or prefer_direct:
            return await self._chat_direct(payload, retries=retries, backoff=backoff)

        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        if self._provider_name and "model" not in payload:
            try:
                from gateway.state import config
                for p in config.providers:
                    if p.name == self._provider_name:
                        payload = dict(payload)
                        payload["model"] = self._model or p.default_model or p.name
                        break
            except Exception:
                pass
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                resp = await self._client.post(
                    f"{self._gateway_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 429 or resp.status_code >= 500:
                    logger.warning("LLM call attempt %d/%d failed with %d: %s", attempt, retries, resp.status_code, resp.text[:200])
                    await asyncio.sleep(backoff * attempt)
                    last_exc = httpx.HTTPStatusError(f"Server error {resp.status_code}", request=resp.request, response=resp)
                    continue
                resp.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning("LLM call attempt %d/%d failed: %s", attempt, retries, exc)
                last_exc = exc
                await asyncio.sleep(backoff * attempt)
        if last_exc:
            raise last_exc
        raise RuntimeError("LLM call failed after retries")

    async def _chat_direct(self, payload: Dict[str, Any], retries: int = 3, backoff: float = 2.0) -> Dict[str, Any]:
        requested_model = payload.get("model", "gateway")
        candidates = _ranked_providers()

        last_exc = None
        for provider in candidates:
            name = provider.get("name", "unknown")
            api_key = _provider_api_key(provider)
            if not api_key:
                continue
            base_url = provider.get("base_url", "").rstrip("/")
            path = provider.get("completions_path", "chat/completions").lstrip("/")
            url = f"{base_url}/{path}"
            model = requested_model
            if model == "gateway":
                model = provider.get("default_model") or name
            proj_payload = dict(payload)
            proj_payload["model"] = model

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            last_err = None
            for attempt in range(1, retries + 1):
                try:
                    resp = await self._client.post(url, headers=headers, json=proj_payload, timeout=20)
                    if resp.status_code == 200:
                        _mark_provider_success(name)
                        return resp.json()
                    if resp.status_code == 429 or resp.status_code >= 500:
                        logger.warning("Direct provider %s attempt %d/%d failed with %d", name, attempt, retries, resp.status_code)
                        await asyncio.sleep(backoff * attempt)
                        last_err = httpx.HTTPStatusError(f"Provider {name} error {resp.status_code}", request=resp.request, response=resp)
                        continue
                    resp.raise_for_status()
                except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                    logger.warning("Direct provider %s attempt %d/%d failed: %s", name, attempt, retries, exc)
                    last_err = exc
                    await asyncio.sleep(backoff * attempt)
            _mark_provider_failure(name)
            last_exc = last_err or last_exc

        if last_exc:
            raise last_exc
        raise RuntimeError("No available direct providers succeeded")

    async def chat(self, text: str, system: Optional[str] = None, temperature: float = 0.7) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self._model or "gateway",
            "messages": [],
            "temperature": temperature,
        }
        if system:
            payload["messages"].append({"role": "system", "content": system})
        payload["messages"].append({"role": "user", "content": text})
        data = await self.chat_completions(payload, prefer_direct=self._direct)
        choices = data.get("choices", [])
        message = choices[0].get("message", {}) if choices else {}
        return {
            "text": message.get("content", ""),
            "model": data.get("model", "unknown"),
            "provider": self._provider_name,
            "usage": data.get("usage", {}),
            "raw": data,
        }

    async def chat_stream(self, payload: Dict[str, Any]) -> AsyncIterator[str]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        async with self._client.stream(
            "POST",
            f"{self._gateway_url}/v1/chat/stream",
            headers=headers,
            json=payload,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    yield line + "\n\n"

    async def close(self) -> None:
        await self._client.aclose()
