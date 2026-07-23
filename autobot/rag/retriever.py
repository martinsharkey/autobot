
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


AUTOBOT_HOME = Path(os.getenv("AUTOBOT_HOME", "."))
_RAG_INDEX = AUTOBOT_HOME / "rag_index.jsonl"


class RagRetriever:
    def __init__(self) -> None:
        self._index_path = _RAG_INDEX
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    def index_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        entry_id = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        entry = {
            "id": entry_id,
            "text": text[:10_000],
            "metadata": metadata or {},
            "indexed_at": time.time(),
        }
        with open(self._index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return entry_id

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self._index_path.exists():
            return []
        results = []
        query_lower = query.lower()
        with open(self._index_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                text = entry.get("text", "")
                if query_lower in text.lower():
                    results.append(entry)
                    if len(results) >= max_results:
                        break
        return results

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
