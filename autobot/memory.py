
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class MemoryEntry:
    text: str
    source: str = "agent"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class MemoryStore:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path(os.getenv("AUTOBOT_HOME", ".")) / "memory"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[MemoryEntry] = []
        self._load()

    def _path(self) -> Path:
        return self._base_dir / "store.json"

    def _load(self) -> None:
        path = self._path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = [MemoryEntry(**entry) for entry in data.get("entries", [])]
            except Exception:
                self._entries = []

    def _save(self) -> None:
        path = self._path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"entries": [entry.to_dict() for entry in self._entries]}, f, indent=2)

    def add(self, text: str, source: str = "agent", metadata: Optional[Dict[str, Any]] = None) -> MemoryEntry:
        entry = MemoryEntry(text=text, source=source, metadata=metadata or {})
        self._entries.append(entry)
        self._save()
        return entry

    def get_recent(self, count: int = 20) -> List[MemoryEntry]:
        return list(sorted(self._entries, key=lambda e: e.created_at, reverse=True)[:count])

    def get_stats(self) -> Dict[str, Any]:
        return {"entries": len(self._entries), "size_bytes": self._path().stat().st_size if self._path().exists() else 0}

    def clear(self) -> None:
        self._entries = []
        self._save()
