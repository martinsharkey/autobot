
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class WindowsShimLayer:
    PATHEXT_EXTENSIONS = [".exe", ".bat", ".cmd", ".ps1", ".com"]

    @classmethod
    def which(cls, name: str) -> Optional[str]:
        path = shutil.which(name)
        if path:
            return path
        for directory in os.environ.get("PATH", "").split(os.pathsep):
            if not directory:
                continue
            base = Path(directory) / name
            for ext in cls.PATHEXT_EXTENSIONS:
                candidate = base.with_suffix(ext)
                if candidate.exists():
                    return str(candidate)
        return None

    @classmethod
    def preserve_windows_env(cls, env: Dict[str, str]) -> Dict[str, str]:
        preserved = dict(env)
        for key in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP"):
            value = os.environ.get(key)
            if value and key not in preserved:
                preserved[key] = value
        return preserved

    @classmethod
    def fallback_terminal(cls, command: str, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        env = cls.preserve_windows_env(os.environ.copy())
        try:
            return subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            if "tmux" in command:
                fallback = command.replace("tmux", "winpty")
                return subprocess.run(
                    fallback,
                    shell=True,
                    cwd=cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            raise


def ensure_windows_compat() -> None:
    if os.name == "nt":
        logger.info("Applying Windows compatibility shims")
        os.which = WindowsShimLayer.which
