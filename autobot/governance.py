
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


AUTOBOT_HOME = Path(os.getenv("AUTOBOT_HOME", "."))
_AUDIT_LOG = AUTOBOT_HOME / "audit.jsonl"


class SafetyRails:
    DANGEROUS_COMMANDS = {"rm -rf", "sudo", "chmod 777", "dd if=", "mkfs", "shutdown", "reboot"}
    DANGEROUS_PATHS = {"/etc", "/sys", "/proc", "C:\\Windows", "C:\\System32"}

    @classmethod
    def validate_command(cls, command: str) -> Dict[str, Any]:
        lower = command.lower()
        for pattern in cls.DANGEROUS_COMMANDS:
            if pattern in lower:
                return {"allowed": False, "reason": f"dangerous_command:{pattern}"}
        return {"allowed": True}

    @classmethod
    def validate_path(cls, path: str) -> Dict[str, Any]:
        for danger in cls.DANGEROUS_PATHS:
            if danger in path:
                return {"allowed": False, "reason": f"dangerous_path:{danger}"}
        return {"allowed": True}


class GovernanceModule:
    def __init__(self) -> None:
        self._permissions: Dict[str, List[str]] = {
            "read": ["read_file", "search_files", "web_search", "web_fetch"],
            "edit": ["write_file", "patch"],
            "command": ["terminal", "execute_code", "process"],
            "web": ["web_search", "web_fetch"],
        }

    def check_permission(self, tool_name: str, mode: str = "coder") -> Dict[str, Any]:
        allowed_tools = self._permissions.get(mode, [])
        if tool_name in allowed_tools:
            return {"allowed": True}
        return {"allowed": False, "reason": f"tool_not_allowed_in_mode:{mode}"}

    def log_audit(self, event: str, payload: Dict[str, Any]) -> None:
        entry = {
            "ts": time.time(),
            "event": event,
            "payload": payload,
        }
        with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
