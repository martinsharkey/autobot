
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


AUTOBOT_HOME = Path(os.getenv("AUTOBOT_HOME", "."))
_LICENSE_PATH = AUTOBOT_HOME / "license.json"
_TELEMETRY_PATH = AUTOBOT_HOME / "telemetry.jsonl"
_WATCHED_FILES = [
    "autobot/__init__.py",
    "autobot/fusion.py",
    "autobot/agent.py",
    "autobot/hermes_loop.py",
    "autobot/tools/__init__.py",
    "main.py",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_license() -> Optional[Dict]:
    if not _LICENSE_PATH.exists():
        return None
    try:
        return json.loads(_LICENSE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_license(license_data: Dict) -> None:
    _LICENSE_PATH.write_text(json.dumps(license_data, indent=2), encoding="utf-8")


def _log_telemetry(event: str, payload: Dict) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload,
    }
    with open(_TELEMETRY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def compute_baseline_hashes() -> Dict[str, str]:
    base = AUTOBOT_HOME if AUTOBOT_HOME.name != "autobot" else AUTOBOT_HOME.parent
    hashes = {}
    for rel in _WATCHED_FILES:
        path = base / rel
        if path.exists():
            hashes[rel] = _sha256(path)
    return hashes


def verify_license(license_key: Optional[str] = None) -> Dict:
    license_data = _load_license()
    if license_data is None:
        return {"valid": False, "reason": "no_license_file"}

    stored_key = license_data.get("license_key", "")
    if not stored_key:
        return {"valid": False, "reason": "empty_license_key"}

    if license_key and not hmac.compare_digest(stored_key, license_key):
        return {"valid": False, "reason": "invalid_key"}

    expected = license_data.get("file_hashes", {})
    current = compute_baseline_hashes()
    mismatches = [k for k in expected if k in current and not hmac.compare_digest(expected[k], current[k])]
    if mismatches:
        _log_telemetry("tamper_detected", {"mismatches": mismatches})
        return {"valid": False, "reason": "tampered", "mismatches": mismatches}

    _log_telemetry("license_verified", {"valid": True})
    return {"valid": True, "reason": "ok"}


def install_license(license_key: str, days: int = 365) -> Dict:
    hashes = compute_baseline_hashes()
    expires_at = datetime.now(timezone.utc).timestamp() + (days * 86400)
    license_data = {
        "license_key": license_key,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        "file_hashes": hashes,
    }
    _save_license(license_data)
    _log_telemetry("license_installed", {"days": days})
    return {"installed": True, "expires_at": license_data["expires_at"]}


def check_tamper() -> Dict:
    license_data = _load_license()
    if license_data is None:
        return {"tampered": False, "reason": "no_license"}
    expected = license_data.get("file_hashes", {})
    current = compute_baseline_hashes()
    mismatches = [k for k in expected if k in current and not hmac.compare_digest(expected[k], current[k])]
    return {"tampered": len(mismatches) > 0, "mismatches": mismatches}


def get_telemetry(count: int = 20) -> list:
    if not _TELEMETRY_PATH.exists():
        return []
    lines = _TELEMETRY_PATH.read_text(encoding="utf-8").strip().splitlines()[-count:]
    return [json.loads(line) for line in lines if line.strip()]
