"""
self_patch.py — safe self-editing utilities for Autobot.

Provides:
  - apply_patch(file_path, old, new): find-replace in a file with backup.
  - restart_gateway(): kill process on port 8001 and restart python main.py.
"""

import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path


def apply_patch(file_path: str, old: str, new: str) -> dict:
    """
    Read *file_path*, replace the first occurrence of *old* with *new*,
    write the result back, and return a dict with the outcome.

    A timestamped backup of the original file is written next to the
    original (or to the system temp directory if the parent is not
    writable).

    Returns
    -------
    dict
        ``{"ok": True, "backup_path": str}`` on success.
        ``{"ok": False, "error": str}`` on failure.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        return {"ok": False, "error": f"File does not exist: {path}"}

    if not path.is_file():
        return {"ok": False, "error": f"Not a regular file: {path}"}

    try:
        original = path.read_text(encoding="utf-8")
    except Exception as exc:
        return {"ok": False, "error": f"Failed to read {path}: {exc}"}

    if old not in original:
        return {
            "ok": False,
            "error": "old string not found in file (first occurrence required)",
        }

    # Perform exactly one replacement (the first occurrence).
    updated = original.replace(old, new, 1)

    # --- Create backup ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_name = f"{path.name}.{timestamp}.bak"

    # Try to write backup alongside the original file first.
    try:
        backup_path = path.with_name(backup_name)
        backup_path.write_text(original, encoding="utf-8")
    except (OSError, PermissionError):
        # Fall back to system temp directory.
        try:
            backup_dir = Path(tempfile.gettempdir())
            backup_path = backup_dir / backup_name
            backup_path.write_text(original, encoding="utf-8")
        except Exception as exc:
            return {"ok": False, "error": f"Failed to write backup: {exc}"}

    # --- Write patched file ---
    try:
        path.write_text(updated, encoding="utf-8")
    except Exception as exc:
        # Restore backup on write failure.
        try:
            path.write_text(original, encoding="utf-8")
        except Exception:
            pass
        return {"ok": False, "error": f"Failed to write patched file: {exc}"}

    return {"ok": True, "backup_path": str(backup_path)}


def restart_gateway() -> dict:
    """
    Kill any process listening on TCP port 8001 (SIGTERM, then SIGKILL
    after a short grace period) and start ``python main.py`` in the
    current working directory.

    Returns
    -------
    dict
        ``{"ok": True, "pid": int}`` if the new process was spawned.
        ``{"ok": False, "error": str}`` on failure.
    """
    # --- Find and kill process on port 8001 ---
    try:
        # lsof is not always available on every platform (notably Windows).
        # Try the cross-platform approach: iterate ``/proc`` on Linux or
        # use ``netstat`` / ``ss`` as a fallback.
        _kill_process_on_port(8001)
    except Exception as exc:
        return {"ok": False, "error": f"Failed to kill existing process: {exc}"}

    # --- Wait for port to become free ---
    for _ in range(15):
        if not _is_port_in_use(8001):
            break
        time.sleep(0.5)
    else:
        return {
            "ok": False,
            "error": "Port 8001 did not become free after killing process",
        }

    # --- Start new gateway ---
    cwd = Path.cwd()
    main_py = cwd / "main.py"
    if not main_py.exists():
        return {"ok": False, "error": f"main.py not found in {cwd}"}

    try:
        proc = subprocess.Popen(
            ["python", "main.py"],
            cwd=str(cwd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return {"ok": False, "error": f"Failed to start gateway: {exc}"}

    return {"ok": True, "pid": proc.pid}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _kill_process_on_port(port: int) -> None:
    """Kill every process listening on *port* (SIGTERM → SIGKILL)."""
    pids = _find_pids_on_port(port)
    if not pids:
        return

    # SIGTERM first
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except (OSError, PermissionError):
            pass

    # Wait a moment, then SIGKILL survivors
    time.sleep(1.0)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except (OSError, PermissionError):
            pass


def _find_pids_on_port(port: int) -> list[int]:
    """Return a list of PIDs listening on *port* (TCP)."""
    pids: set[int] = set()

    # Strategy 1: ``ss`` (modern Linux)
    try:
        out = subprocess.check_output(
            ["ss", "-tlnp", f"sport = :{port}"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode()
        pids |= _extract_pids_from_ss(out)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    # Strategy 2: ``netstat`` (BSD / older Linux / macOS)
    try:
        out = subprocess.check_output(
            ["netstat", "-tlnp"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode()
        pids |= _extract_pids_from_netstat(out, port)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    # Strategy 3: ``/proc/net/tcp`` (Linux fallback)
    try:
        pids |= _find_pids_via_proc(port)
    except (FileNotFoundError, PermissionError):
        pass

    return list(pids)


def _extract_pids_from_ss(output: str) -> set[int]:
    """Parse ``ss -tlnp`` output and return PIDs."""
    pids: set[int] = set()
    for line in output.splitlines():
        # Typical: LISTEN 0 128 0.0.0.0:8001 0.0.0.0:* users:(("python",pid=12345,fd=3))
        if "pid=" in line:
            for token in line.split():
                if "pid=" in token:
                    raw = token.split("pid=")[1].rstrip(",)")
                    try:
                        pids.add(int(raw))
                    except ValueError:
                        pass
    return pids


def _extract_pids_from_netstat(output: str, port: int) -> set[int]:
    """Parse ``netstat -tlnp`` output for the given port and return PIDs."""
    pids: set[int] = set()
    port_str = f":{port}"
    for line in output.splitlines():
        if port_str in line and "LISTEN" in line:
            # The PID/Program name is usually the last column: ``12345/python``
            parts = line.rsplit(None, 1)
            if len(parts) == 2:
                pid_part = parts[1].split("/")[0]
                try:
                    pids.add(int(pid_part))
                except ValueError:
                    pass
    return pids


def _find_pids_via_proc(port: int) -> set[int]:
    """Parse ``/proc/net/tcp`` for the hex-encoded port and resolve PIDs."""
    proc_net = Path("/proc/net/tcp")
    if not proc_net.exists():
        return set()

    port_le = f"{port:02X}{port // 256:02X}"  # little-endian encoding

    pids: set[int] = set()
    lines = proc_net.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) < 2:
            continue
        local_addr = parts[1]  # e.g. "00000000:411F"
        if ":" in local_addr:
            _, hex_port = local_addr.rsplit(":", 1)
            if hex_port.upper() == port_le:
                inode = parts[9] if len(parts) > 9 else ""
                if inode:
                    pids |= _pids_for_inode(inode)
    return pids


def _pids_for_inode(inode: str) -> set[int]:
    """Scan /proc/*/fd for symlinks matching a socket inode."""
    pids: set[int] = set()
    proc = Path("/proc")
    for proc_dir in proc.iterdir():
        if not proc_dir.name.isdigit():
            continue
        fd_dir = proc_dir / "fd"
        try:
            for fd_entry in fd_dir.iterdir():
                try:
                    target = os.readlink(str(fd_entry))
                    if f"socket:[{inode}]" in target:
                        pids.add(int(proc_dir.name))
                except (OSError, ValueError):
                    continue
        except PermissionError:
            continue
    return pids


def _is_port_in_use(port: int) -> bool:
    """Return True if any process is listening on TCP *port* (best-effort)."""
    return bool(_find_pids_on_port(port))
