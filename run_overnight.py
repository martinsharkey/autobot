#!/usr/bin/env python3
"""Run overnight learning loop."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from autobot.overnight import OvernightLearner


def main() -> int:
    learner = OvernightLearner()
    if not learner.should_run():
        print(f"Overnight learner ran recently ({learner.time_since_last_run():.1f}s ago). Skipping.")
        return 0
    result = asyncio.run(learner.run_once())
    print(f"Overnight learning complete. Report: {result.get('report_path')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
