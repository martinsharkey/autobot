
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_DIR = Path(__file__).resolve().parent.parent
BLUE_DIR = PROJECT_DIR / "autobot-blue"
GREEN_DIR = PROJECT_DIR / "autobot-green"
ACTIVE_LINK = PROJECT_DIR / "autobot-active"


def _current_active() -> Optional[Path]:
    if ACTIVE_LINK.exists():
        target = ACTIVE_LINK.resolve()
        if target.exists():
            return target
    return None


def _hash_dir(path: Path) -> str:
    h = hashlib.sha256()
    for file in sorted(path.rglob("*.py")):
        if file.is_file():
            h.update(str(file.relative_to(path)).encode())
            h.update(file.read_bytes())
    return h.hexdigest()[:16]


def prepare_release(source_dir: Optional[Path] = None) -> Dict[str, Any]:
    source_dir = source_dir or PROJECT_DIR
    inactive = GREEN_DIR if _current_active() == BLUE_DIR else BLUE_DIR
    if inactive.exists():
        shutil.rmtree(inactive)
    shutil.copytree(source_dir, inactive, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    return {
        "active": str(_current_active()),
        "staging": str(inactive),
        "source_hash": _hash_dir(source_dir),
        "staging_hash": _hash_dir(inactive),
    }


def validate_release(staging_dir: Optional[Path] = None) -> Dict[str, Any]:
    staging_dir = staging_dir or (GREEN_DIR if _current_active() == BLUE_DIR else BLUE_DIR)
    if not staging_dir.exists():
        return {"valid": False, "reason": "staging_dir_missing"}
    try:
        init_file = staging_dir / "autobot" / "__init__.py"
        if not init_file.exists():
            return {"valid": False, "reason": "missing_init", "detail": str(init_file)}
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(init_file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {"valid": False, "reason": "compile_error", "detail": result.stderr[:500]}
        return {"valid": True, "staging": str(staging_dir)}
    except Exception as exc:
        return {"valid": False, "reason": str(exc)}


def promote_release() -> Dict[str, Any]:
    staging = GREEN_DIR if _current_active() == BLUE_DIR else BLUE_DIR
    if not staging.exists():
        return {"promoted": False, "reason": "staging_dir_missing"}
    validation = validate_release(staging)
    if not validation.get("valid"):
        return {"promoted": False, "reason": "validation_failed", "detail": validation}
    if ACTIVE_LINK.exists():
        ACTIVE_LINK.unlink()
    ACTIVE_LINK.symlink_to(staging)
    return {"promoted": True, "active": str(ACTIVE_LINK.resolve())}


def rollback() -> Dict[str, Any]:
    current = _current_active()
    if current == BLUE_DIR:
        target = GREEN_DIR
    elif current == GREEN_DIR:
        target = BLUE_DIR
    else:
        target = BLUE_DIR
    if not target.exists():
        return {"rolled_back": False, "reason": "target_missing"}
    if ACTIVE_LINK.exists():
        ACTIVE_LINK.unlink()
    ACTIVE_LINK.symlink_to(target)
    return {"rolled_back": True, "active": str(ACTIVE_LINK.resolve())}
