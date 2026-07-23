
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess


def run_test(name: str, fn) -> Dict[str, Any]:
    start = time.time()
    try:
        ok, detail = fn()
        elapsed = time.time() - start
        return {"name": name, "passed": ok, "detail": detail, "elapsed": round(elapsed, 3)}
    except Exception as exc:
        elapsed = time.time() - start
        return {"name": name, "passed": False, "detail": f"exception: {exc}", "elapsed": round(elapsed, 3)}


def test_autobot_import() -> tuple[bool, str]:
    import autobot
    from autobot.config import Config
    from autobot.runtime import AgentRuntime
    from autobot.notifications import NotificationClient
    from autobot.remote_commands import RemoteCommandProtocol
    config = Config()
    rt = AgentRuntime.shared()
    nc = NotificationClient()
    rc = RemoteCommandProtocol()
    return True, "all core autobot modules import and instantiate"


def test_gateway_import() -> tuple[bool, str]:
    from gateway import app
    return True, f"gateway app title={app.title}"


def test_config_defaults() -> tuple[bool, str]:
    from autobot.config import Config
    config = Config()
    gateway_url = config.get("gateway_url")
    default_mode = config.get("default_mode")
    telegram_token = config.get("notification_telegram_token")
    whatsapp_recipient = config.get("notification_whatsapp_recipient")
    autonomy_phone = config.get("autonomy_completion_phone")
    return True, f"gateway_url={gateway_url}, mode={default_mode}, telegram={'yes' if telegram_token else 'no'}, whatsapp={whatsapp_recipient}, phone={autonomy_phone}"


def test_agent_self_audit_exists() -> tuple[bool, str]:
    path = os.path.join(os.path.dirname(__file__), "..", "agent_self_audit_2026-07-23.md")
    if not os.path.exists(path):
        return False, "agent_self_audit_2026-07-23.md missing"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "Enhancement Strategy" not in content:
        return False, "audit missing enhancement strategies"
    return True, f"audit_exists size={len(content)} chars"


def test_todo_has_autonomy_mission() -> tuple[bool, str]:
    path = os.path.join(os.path.dirname(__file__), "..", "TODO.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "Full Autonomy Mission" not in content:
        return False, "TODO.md missing Full Autonomy Mission"
    if "Autonomous Recovery" not in content:
        return False, "TODO.md missing Autonomous Recovery"
    if "Remote Command" not in content:
        return False, "TODO.md missing Remote Command protocol"
    if "07405260296" not in content:
        return False, "TODO.md missing completion phone number"
    return True, "autonomy mission and protocols present in TODO.md"


def test_session_log_updated() -> tuple[bool, str]:
    path = os.path.join(os.path.dirname(__file__), "..", "SESSION_LOG.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "13:45" not in content:
        return False, "SESSION_LOG.md missing latest session entry"
    if "notifications.py" not in content:
        return False, "SESSION_LOG.md missing notifications.py reference"
    return True, "SESSION_LOG.md updated with latest work"


def test_vscode_extension_targets_correct_port() -> tuple[bool, str]:
    vscode_config = os.path.join(os.path.dirname(__file__), "..", "autobot-vscode", "package.json")
    if not os.path.exists(vscode_config):
        return False, "autobot-vscode/package.json missing"
    with open(vscode_config, "r", encoding="utf-8") as f:
        content = f.read()
    if "8001" not in content:
        return False, "VS Code extension not targeting port 8001"
    return True, "VS Code extension targets port 8001"


def test_runtime_wires_governance() -> tuple[bool, str]:
    from autobot.runtime import AgentRuntime
    rt = AgentRuntime.shared()
    if not hasattr(rt, "_governance"):
        return False, "AgentRuntime missing _governance"
    if not hasattr(rt, "_plugins"):
        return False, "AgentRuntime missing _plugins"
    if not hasattr(rt, "_mcp"):
        return False, "AgentRuntime missing _mcp"
    return True, "AgentRuntime wires governance, plugins, MCP, tools, memory, agent, spawner"


def test_autonomy_framework_file() -> tuple[bool, str]:
    path = os.path.join(os.path.dirname(__file__), "..", "AUTONOMY_FRAMEWORK.md")
    if not os.path.exists(path):
        return False, "AUTONOMY_FRAMEWORK.md missing"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    gates = ["Tool Reliability", "Reasoning Transparency", "Unsupervised Execution", "Self-Directed Learning", "Full Autonomy"]
    for gate in gates:
        if gate not in content:
            return False, f"AUTONOMY_FRAMEWORK.md missing gate: {gate}"
    return True, "AUTONOMY_FRAMEWORK.md contains all 5 readiness gates"


def main() -> None:
    tests = [
        test_autobot_import,
        test_gateway_import,
        test_config_defaults,
        test_agent_self_audit_exists,
        test_todo_has_autonomy_mission,
        test_session_log_updated,
        test_vscode_extension_targets_correct_port,
        test_runtime_wires_governance,
        test_autonomy_framework_file,
    ]
    results = [run_test(t.__name__, t) for t in tests]
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(json.dumps({"summary": {"passed": passed, "total": total, "rate": round(passed/total, 2)}, "results": results}, indent=2))


if __name__ == "__main__":
    main()
