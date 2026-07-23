
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


AUTOBOT_HOME = Path(os.getenv("AUTOBOT_HOME", "."))
_RESOURCE_CATALOG_PATH = AUTOBOT_HOME / "resource_catalog.json"


_FREE_RESOURCE_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "github-gist",
        "category": "storage",
        "name": "GitHub Gist",
        "description": "Free code snippet hosting via GitHub Gist API.",
        "cost": "free",
        "setup": ["GITHUB_TOKEN"],
        "limits": "100 requests/min, 10MB per gist",
    },
    {
        "id": "github-pages",
        "category": "hosting",
        "name": "GitHub Pages",
        "description": "Free static site hosting for public repos.",
        "cost": "free",
        "setup": ["GITHUB_TOKEN"],
        "limits": "1GB storage, 100GB bandwidth/month",
    },
    {
        "id": "arxiv",
        "category": "research",
        "name": "arXiv",
        "description": "Free academic paper access via public API.",
        "cost": "free",
        "setup": [],
        "limits": "3 requests/sec, no auth required",
    },
    {
        "id": "duckduckgo",
        "category": "search",
        "name": "DuckDuckGo",
        "description": "Free web search via HTML endpoint.",
        "cost": "free",
        "setup": [],
        "limits": "Rate-limited, no auth required",
    },
    {
        "id": "github-copilot-free",
        "category": "model",
        "name": "GitHub Models",
        "description": "Free LLM inference for limited models.",
        "cost": "free",
        "setup": ["GITHUB_TOKEN"],
        "limits": "Varies by model, free tier available",
    },
    {
        "id": "openrouter-free",
        "category": "model",
        "name": "OpenRouter Free Models",
        "description": "Free LLM endpoints via OpenRouter.",
        "cost": "free",
        "setup": ["OPENROUTER_API_KEY"],
        "limits": "Rate-limited, model-dependent",
    },
    {
        "id": "google-fact-check",
        "category": "verification",
        "name": "Google Fact Check Tools",
        "description": "Free fact-checking API.",
        "cost": "free",
        "setup": ["GOOGLE_API_KEY"],
        "limits": "100 requests/day free tier",
    },
]


class CuriosityProtocol:
    def __init__(self) -> None:
        self._catalog: List[Dict[str, Any]] = list(_FREE_RESOURCE_CATALOG)
        self._available: Dict[str, Dict[str, Any]] = {}
        self._last_scan: float = 0.0

    def scan_resources(self) -> Dict[str, Any]:
        available = []
        for resource in self._catalog:
            required = resource.get("setup", [])
            has_creds = all(os.getenv(var) for var in required) if required else True
            entry = dict(resource)
            entry["available"] = has_creds
            available.append(entry)
            self._available[resource["id"]] = entry
        self._last_scan = time.time()
        return {
            "scanned_at": self._last_scan,
            "total": len(available),
            "available": sum(1 for r in available if r["available"]),
            "resources": available,
        }

    def recommend(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._available:
            self.scan_resources()
        candidates = list(self._available.values())
        if category:
            candidates = [r for r in candidates if r.get("category") == category]
        candidates = [r for r in candidates if r.get("available")]
        candidates.sort(key=lambda r: r.get("cost", "") != "free")
        return candidates

    def refresh_catalog(self, extra: Optional[List[Dict[str, Any]]] = None) -> None:
        if extra:
            self._catalog.extend(extra)
        self._last_scan = 0.0

    def export_catalog(self, path: Optional[Path] = None) -> Path:
        path = path or _RESOURCE_CATALOG_PATH
        path.write_text(json.dumps(self._catalog, indent=2), encoding="utf-8")
        return path
