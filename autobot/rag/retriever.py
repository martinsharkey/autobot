
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SemanticRagRetriever:
    def __init__(self, index_path: Optional[Path] = None) -> None:
        self._index_path = index_path or (Path(os.getenv("AUTOBOT_HOME", ".")) / "rag_index.jsonl")
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    def index_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        entry_id = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        entry = {
            "id": entry_id,
            "text": text[:5000],
            "metadata": metadata or {},
            "indexed_at": time.time(),
            "keywords": list(set(re.findall(r"[a-zA-Z]{3,}", text.lower())))[:50],
        }
        with open(self._index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return entry_id

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self._index_path.exists():
            return []
        query_keywords = set(re.findall(r"[a-zA-Z]{3,}", query.lower()))
        scored: List[tuple[float, Dict[str, Any]]] = []
        with open(self._index_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                keywords = set(entry.get("keywords", []))
                overlap = len(query_keywords & keywords)
                score = overlap / max(len(query_keywords), 1)
                if score > 0:
                    scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:max_results]]

    def get_citations(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        results = self.search(query, max_results=max_results)
        citations = []
        for entry in results:
            citations.append({
                "id": entry.get("id", ""),
                "source": entry.get("metadata", {}).get("source", "rag"),
                "snippet": entry.get("text", "")[:200],
            })
        return citations
