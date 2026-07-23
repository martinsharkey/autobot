
from __future__ import annotations

import httpx
import os
from typing import Any, AsyncIterator, Dict, Optional

AUTOBOT_GATEWAY = os.getenv("AUTOBOT_GATEWAY", "http://127.0.0.1:8001")
AUTOBOT_API_KEY = os.getenv("AUTOBOT_API_KEY", "changeme")


class LLMClient:
    def __init__(
        self,
        gateway_url: str = AUTOBOT_GATEWAY,
        api_key: str = AUTOBOT_API_KEY,
    ) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=120)

    async def chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        resp = await self._client.post(
            f"{self._gateway_url}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

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
