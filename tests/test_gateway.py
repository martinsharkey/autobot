
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import httpx

GATEWAY_URL = "http://127.0.0.1:8001"
HEADERS = {"Authorization": "Bearer changeme", "Content-Type": "application/json"}


def run_test(name: str, fn) -> Dict[str, Any]:
    start = time.time()
    try:
        ok, detail = fn()
        elapsed = time.time() - start
        return {"name": name, "passed": ok, "detail": detail, "elapsed": round(elapsed, 3)}
    except Exception as exc:
        elapsed = time.time() - start
        return {"name": name, "passed": False, "detail": f"exception: {exc}", "elapsed": round(elapsed, 3)}


def test_health() -> tuple[bool, str]:
    r = httpx.get(f"{GATEWAY_URL}/v1/health", headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"health status {r.status_code}"
    data = r.json()
    if data.get("status") != "ok":
        return False, f"health status not ok: {data}"
    return True, f"providers={data.get('provider_count')}"


def test_providers() -> tuple[bool, str]:
    r = httpx.get(f"{GATEWAY_URL}/v1/providers", headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"providers status {r.status_code}"
    data = r.json()
    providers = data.get("providers", [])
    if not providers:
        return False, "no providers"
    active = [p for p in providers if p.get("active")]
    return True, f"active_providers={len(active)}/{len(providers)}"


def test_chat_completions() -> tuple[bool, str]:
    payload = {"model": "gateway", "messages": [{"role": "user", "content": "Say x in 1 word"}]}
    r = httpx.post(f"{GATEWAY_URL}/v1/chat/completions", json=payload, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        return False, f"chat status {r.status_code}: {r.text[:200]}"
    data = r.json()
    choices = data.get("choices", [])
    if not choices:
        return False, "no choices"
    content = choices[0].get("message", {}).get("content", "")
    return True, f"response={content[:80]!r}"


def test_memory_endpoint() -> tuple[bool, str]:
    r = httpx.get(f"{GATEWAY_URL}/v1/memory", headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"memory status {r.status_code}"
    data = r.json()
    entries = data.get("entries", [])
    stats = data.get("stats", {})
    return True, f"entries={len(entries)}, stats={stats}"


def test_skills_endpoint() -> tuple[bool, str]:
    r = httpx.get(f"{GATEWAY_URL}/v1/skills", headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"skills status {r.status_code}"
    data = r.json()
    skills = data.get("skills", [])
    return True, f"skills={len(skills)}"


def test_agent_status() -> tuple[bool, str]:
    r = httpx.get(f"{GATEWAY_URL}/v1/agent/status", headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"agent status {r.status_code}"
    data = r.json()
    active = data.get("active_tasks", 0)
    return True, f"active_tasks={active}"


def test_agent_run_non_streaming() -> tuple[bool, str]:
    payload = {"goal": "Say hi in 1 word", "mode": "coder", "stream": False}
    r = httpx.post(f"{GATEWAY_URL}/v1/agent/run", json=payload, headers=HEADERS, timeout=180)
    if r.status_code != 200:
        return False, f"agent run status {r.status_code}: {r.text[:200]}"
    data = r.json()
    result = data.get("result", "")
    task_id = data.get("task_id", "")
    if not task_id:
        return False, "missing task_id"
    return True, f"task_id={task_id}, result={result[:60]!r}"


def main() -> None:
    tests = [
        test_health,
        test_providers,
        test_chat_completions,
        test_memory_endpoint,
        test_skills_endpoint,
        test_agent_status,
        test_agent_run_non_streaming,
    ]
    results = [run_test(t.__name__, t) for t in tests]
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(json.dumps({"summary": {"passed": passed, "total": total, "rate": round(passed/total, 2)}, "results": results}, indent=2))


if __name__ == "__main__":
    main()
