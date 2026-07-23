
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


WORK_DIR = Path(os.getenv("AUTOBOT_HOME", ".")) / "compute"
TASK_QUEUE = WORK_DIR / "task_queue.jsonl"
RESULT_QUEUE = WORK_DIR / "result_queue.jsonl"


def _ensure_work_dir() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)


def enqueue_task(task: Dict[str, Any]) -> None:
    _ensure_work_dir()
    task["queued_at"] = time.time()
    with open(TASK_QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps(task) + "\n")


def dequeue_task(worker_id: str) -> Optional[Dict[str, Any]]:
    _ensure_work_dir()
    if not TASK_QUEUE.exists():
        return None
    lines = TASK_QUEUE.read_text(encoding="utf-8").strip().splitlines()
    if not lines:
        return None
    task = json.loads(lines[0])
    task["picked_by"] = worker_id
    task["picked_at"] = time.time()
    remaining = lines[1:]
    TASK_QUEUE.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    return task


def publish_result(task_id: str, result: Any, status: str = "ok") -> None:
    _ensure_work_dir()
    entry = {"task_id": task_id, "status": status, "result": result, "finished_at": time.time()}
    with open(RESULT_QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


async def run_worker(worker_id: str, concurrency: int = 1) -> None:
    from autobot.subagent import SubAgentSpawner

    spawner = SubAgentSpawner()
    active = 0
    while True:
        if active < concurrency:
            task = dequeue_task(worker_id)
            if task:
                active += 1
                result = await spawner.spawn(
                    task.get("task", ""),
                    mode=task.get("mode", "coder"),
                    context={"worker_id": worker_id, "task_id": task.get("id")},
                )
                publish_result(task.get("id", ""), result)
                active -= 1
                continue
        await asyncio.sleep(1)
