
from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from autobot.memory import MemoryStore


AUTOBOT_HOME = Path(os.getenv("AUTOBOT_HOME", "."))


class OvernightLearner:
    def __init__(self, session_gap_seconds: float = 3600.0) -> None:
        self._session_gap = session_gap_seconds
        self._last_run_at: Optional[float] = None
        self._report_path = AUTOBOT_HOME / "overnight_report.md"

    def time_since_last_run(self) -> float:
        if self._last_run_at is None:
            return float("inf")
        return time.time() - self._last_run_at

    def should_run(self) -> bool:
        return self.time_since_last_run() >= self._session_gap

    def run_curator(self) -> dict:
        _HERMES_DIR = str(Path(__file__).resolve().parent.parent.parent / "hermes-repo")
        if _HERMES_DIR not in sys.path:
            sys.path.append(_HERMES_DIR)
        from agent.curator import run_curator_review, apply_automatic_transitions, load_state, save_state

        transitions = apply_automatic_transitions()
        summary = run_curator_review(synchronous=True, dry_run=False, consolidate=True)
        state = load_state()
        state["last_run_at"] = time.time()
        state["run_count"] = state.get("run_count", 0) + 1
        state["last_run_summary"] = summary
        state["last_run_summary_shown_at"] = time.time()
        save_state(state)
        self._last_run_at = time.time()
        return {"summary": summary.get("summary_so_far") if isinstance(summary, dict) else summary, "transitions": transitions, "state": state}

    def write_report(self, result: dict) -> Path:
        summary = result.get("summary") or result.get("summary_so_far") or "No summary available."
        if isinstance(summary, dict):
            summary = summary.get("text") or summary.get("summary") or str(summary)
        transitions = result.get("transitions") or result.get("auto_transitions") or {}
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            f"# Overnight Learning Report — {now}",
            "",
            "## Curator Summary",
            str(summary),
            "",
            "## Automatic Transitions",
            f"Total transitions: {len(transitions) if isinstance(transitions, dict) else 'N/A'}",
            "",
        ]
        if isinstance(transitions, dict) and transitions:
            for skill, count in transitions.items():
                lines.append(f"- {skill}: {count}")
        else:
            lines.append("- No transitions applied.")

        self._report_path.write_text("\n".join(lines), encoding="utf-8")
        return self._report_path

    async def run_once(self) -> dict:
        result = self.run_curator()
        report_path = self.write_report(result)
        result["report_path"] = str(report_path)
        return result
