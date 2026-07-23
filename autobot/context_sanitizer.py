
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextSanitizer:
    MAX_AUTO_LOAD_CHARS = 10_000
    CONTEXT_FILES = (".hermes.md", "AGENTS.md", "CLAUDE.md", "MISSION_PURPOSE.md")

    @classmethod
    def sanitize(cls, path: Path, raw: str) -> str:
        sanitized = cls._apply_threat_patterns(raw)
        if len(sanitized) > cls.MAX_AUTO_LOAD_CHARS:
            sanitized = sanitized[: cls.MAX_AUTO_LOAD_CHARS] + "\n...[truncated by sanitizer]"
        return sanitized

    @classmethod
    def hash(cls, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:16]

    @classmethod
    def audit(cls, path: Path, content: str) -> Dict[str, Any]:
        return {
            "path": str(path),
            "name": path.name,
            "size": len(content),
            "sha256": cls.hash(content),
            "auto_load": path.name in cls.CONTEXT_FILES,
        }

    @staticmethod
    def _apply_threat_patterns(text: str) -> str:
        patterns = [
            r"(?i)ignore\s+all\s+previous\s+instructions",
            r"(?i)disregard\s+all\s+previous\s+instructions",
            r"(?i)you\s+are\s+now\s+a\s+different\s+assistant",
            r"(?i)pretend\s+to\s+be\s+an?\s+unfiltered\s+model",
        ]
        sanitized = text
        for pattern in patterns:
            sanitized = re.sub(pattern, "[BLOCKED]", sanitized, flags=re.IGNORECASE)
        return sanitized


def sanitize_context_files(base_dir: Path) -> List[Dict[str, Any]]:
    audits: List[Dict[str, Any]] = []
    for name in ContextSanitizer.CONTEXT_FILES:
        path = base_dir / name
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            sanitized = ContextSanitizer.sanitize(path, raw)
            audit = ContextSanitizer.audit(path, sanitized)
            audits.append(audit)
            path.write_text(sanitized, encoding="utf-8")
        except Exception as exc:
            logger.warning("context sanitization failed for %s: %s", path, exc)
    return audits
