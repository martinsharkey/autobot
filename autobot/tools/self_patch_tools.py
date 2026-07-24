from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

APPLY_PATCH_SCHEMA = {
    "name": "apply_patch",
    "description": "Replace the first occurrence of a specific block of text in a file with a new block of text. Also creates a timestamped backup of the original file.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the target file to modify."
            },
            "old": {
                "type": "string",
                "description": "The exact block of text to be replaced (including indentation)."
            },
            "new": {
                "type": "string",
                "description": "The replacement text block."
            }
        },
        "required": ["file_path", "old", "new"]
    }
}

RESTART_GATEWAY_SCHEMA = {
    "name": "restart_gateway",
    "description": "Kill any process listening on TCP port 8001 and restart the python gateway (main.py) in the background.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}


def handle_apply_patch(args: Dict[str, Any], **kw) -> str:
    from autobot.self_patch import apply_patch
    file_path = args.get("file_path", "")
    old = args.get("old", "")
    new = args.get("new", "")
    
    if not file_path or not old:
        return "Error: file_path and old content are required."
        
    res = apply_patch(file_path, old, new)
    if res.get("ok"):
        return f"Successfully applied patch to {file_path}. Backup created at {res.get('backup_path')}"
    else:
        return f"Failed to apply patch: {res.get('error')}"


def handle_restart_gateway(args: Dict[str, Any], **kw) -> str:
    from autobot.self_patch import restart_gateway
    res = restart_gateway()
    if res.get("ok"):
        return f"Successfully restarted gateway server (PID: {res.get('pid')})."
    else:
        return f"Failed to restart gateway: {res.get('error')}"


def register_self_patch_tools(registry: Any) -> None:
    # Register apply_patch
    registry.register(
        name="apply_patch",
        toolset="file",
        schema=APPLY_PATCH_SCHEMA,
        handler=handle_apply_patch,
        description=APPLY_PATCH_SCHEMA["description"],
        emoji="🔧"
    )
    # Register restart_gateway
    registry.register(
        name="restart_gateway",
        toolset="terminal",
        schema=RESTART_GATEWAY_SCHEMA,
        handler=handle_restart_gateway,
        description=RESTART_GATEWAY_SCHEMA["description"],
        emoji="🔄"
    )
