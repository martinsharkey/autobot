
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from autobot.config import Config

TASK_HINTS = {
    "code": ["code", "implement", "refactor", "debug", "fix", "build", "function", "class", "api", "test"],
    "research": ["research", "find", "search", "look up", "summarize", "analyze", "paper", "article"],
    "trading": ["trade", "stock", "market", "ticker", "invest", "portfolio", "AAPL", "TSLA", "MSFT"],
    "chat": ["hello", "hi", "explain", "what is", "how does", "why"],
}


@dataclass(frozen=True)
class RouteDecision:
    provider: str
    model: str
    reason: str


def classify_task(goal: str) -> str:
    lower = goal.lower()
    scores = {category: sum(1 for hint in hints if hint in lower) for category, hints in TASK_HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "chat"


def select_model(goal: str, providers: List[str], provider_map: Dict[str, Dict[str, str]]) -> Optional[RouteDecision]:
    category = classify_task(goal)
    candidates = []

    coding_models = {
        "deepseek": "deepseek-chat",
        "openrouter": "meta-llama/llama-3.1-8b-instruct",
        "together-ai": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    }
    research_models = {
        "openrouter": "meta-llama/llama-3.1-70b-instruct",
        "deepinfra": "meta-llama/Llama-3.3-70B-Instruct",
    }
    trading_models = {
        "deepseek": "deepseek-chat",
        "openrouter": "meta-llama/llama-3.1-70b-instruct",
    }

    preferred = {
        "code": coding_models,
        "research": research_models,
        "trading": trading_models,
        "chat": coding_models,
    }.get(category, coding_models)

    for provider, model in preferred.items():
        if provider in providers and provider_map.get(provider, {}).get("has_api_key"):
            candidates.append(RouteDecision(provider=provider, model=model, reason=f"task={category}"))

    if not candidates:
        for provider in providers:
            if provider_map.get(provider, {}).get("has_api_key"):
                candidates.append(RouteDecision(provider=provider, model="", reason="fallback"))

    return candidates[0] if candidates else None


def _route_providers(payload, providers):
    try:
        messages = payload.get("messages") or []
        goal = ""
        for msg in messages:
            if msg.get("role") == "user":
                goal = msg.get("content", "")
                break
        provider_map = {p.name: {"has_api_key": True} for p in providers}
        decision = select_model(goal, [p.name for p in providers], provider_map)
        if decision and decision.provider:
            ordered = [p for p in providers if p.name == decision.provider]
            remainder = [p for p in providers if p.name != decision.provider]
            return ordered + remainder
    except Exception:
        pass
    return providers
