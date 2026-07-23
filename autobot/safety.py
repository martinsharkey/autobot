
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SafetyPolicy:
    def __init__(self, policy_path: Optional[Path] = None) -> None:
        self._policy_path = policy_path or (Path(os.getenv("AUTOBOT_HOME", ".")) / "safety_policy.json")
        self._policy: Dict[str, Any] = {
            "allow_destructive_fs": False,
            "allowed_network_hosts": [],
            "max_memory_mb": 500,
            "max_cpu_percent": 80,
            "kill_switch_enabled": True,
        }
        self._abort_flag = False
        self._load()

    def _load(self) -> None:
        if self._policy_path.exists():
            try:
                with open(self._policy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._policy.update(data)
            except Exception:
                pass

    def save(self) -> None:
        try:
            self._policy_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._policy_path, "w", encoding="utf-8") as f:
                json.dump(self._policy, f, indent=2)
        except Exception:
            pass

    def check(self, action: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._policy.get("kill_switch_enabled", True):
            return {"allowed": True}
        if action in ("write_file", "patch", "execute_code", "terminal"):
            if not self._policy.get("allow_destructive_fs", False):
                path = arguments.get("path") or arguments.get("command", "")
                if any(keyword in str(path).lower() for keyword in ("/etc", "/sys", "/proc", "system32", "shutdown", "rm -rf")):
                    return {"allowed": False, "reason": "destructive_action_blocked"}
        return {"allowed": True}

    def abort(self) -> None:
        self._abort_flag = True

    def reset_abort(self) -> None:
        self._abort_flag = False

    def is_aborted(self) -> bool:
        return self._abort_flag
