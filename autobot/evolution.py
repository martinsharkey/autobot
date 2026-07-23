
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from autobot.memory import MemoryStore


_SCAN_DIRS = [
    Path("autobot"),
    Path("main.py"),
]


class GapAnalysisEngine:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path(os.getenv("AUTOBOT_HOME", "."))

    def _iter_targets(self):
        for target in _SCAN_DIRS:
            path = self._base_dir / target
            if path.is_dir():
                for py in path.rglob("*.py"):
                    yield py
            elif path.is_file():
                yield path

    def scan(self) -> List[Dict[str, Any]]:
        gaps = []
        for path in self._iter_targets():
            rel = path.relative_to(self._base_dir)
            text = path.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("# TODO") or stripped.startswith("# FIXME") or stripped.startswith("# IMPLEMENT"):
                    gaps.append({
                        "file": str(rel),
                        "line": i,
                        "type": "todo",
                        "text": stripped,
                    })
            try:
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and (node.body == [] or (len(node.body) == 1 and isinstance(node.body[0], ast.Pass))):
                        gaps.append({
                            "file": str(rel),
                            "line": node.lineno,
                            "type": "empty_function",
                            "text": f"def {node.name}(...)",
                        })
            except SyntaxError:
                continue
        return gaps

    def summarize(self) -> Dict[str, Any]:
        gaps = self.scan()
        by_type: Dict[str, int] = {}
        for gap in gaps:
            by_type[gap["type"]] = by_type.get(gap["type"], 0) + 1
        return {"total": len(gaps), "by_type": by_type, "samples": gaps[:10]}

    def log_gaps(self, memory: Optional[MemoryStore] = None) -> Dict[str, Any]:
        memory = memory or MemoryStore()
        summary = self.summarize()
        memory.add(
            f"Gap analysis: {summary['total']} gaps found ({summary['by_type']})",
            source="evolution",
            metadata={"gap_analysis": summary},
        )
        return summary
