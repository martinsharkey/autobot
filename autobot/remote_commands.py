
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from autobot.notifications import NotificationClient
from autobot.runtime import AgentRuntime

logger = logging.getLogger(__name__)

class RemoteCommandProtocol:
    def __init__(self) -> None:
        self._notifier = NotificationClient()
        self._runtime = AgentRuntime.shared()

    def handle_telegram_update(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        message = update.get("message") or update.get("channel_post") or {}
        text = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id", ""))
        if not text or not chat_id:
            return None
        return self._dispatch_command(text.strip(), source="telegram", chat_id=chat_id)

    def handle_whatsapp_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        entry = ((payload.get("entry") or [{}]))[0]
        changes = ((entry.get("changes") or [{}]))[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None
        msg = messages[0]
        text = msg.get("text", {}).get("body", "")
        recipient = msg.get("to", "")
        if not text:
            return None
        return self._dispatch_command(text.strip(), source="whatsapp", recipient=recipient)

    def _dispatch_command(self, text: str, source: str, **context) -> Optional[Dict[str, Any]]:
        if text.startswith("/"):
            return self._handle_slash_command(text, source, **context)
        return None

    def _handle_slash_command(self, text: str, source: str, **context) -> Dict[str, Any]:
        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:]
        if cmd == "/status":
            return {"command": "status", "source": source, "result": "operational"}
        if cmd == "/run":
            goal = " ".join(args)
            if not goal:
                return {"command": "run", "source": source, "error": "missing goal"}
            import asyncio
            result = asyncio.run(self._runtime.execute(goal, mode="coder"))
            return {"command": "run", "source": source, "goal": goal, "result": result}
        if cmd == "/evolve":
            import asyncio
            result = asyncio.run(self._runtime.evolve())
            return {"command": "evolve", "source": source, "result": result}
        if cmd == "/recover":
            import asyncio
            result = asyncio.run(self._runtime.overnight())
            return {"command": "recover", "source": source, "result": result}
        return {"command": cmd, "source": source, "error": "unknown_command"}

    def autonomous_recovery(self, failure_reason: str) -> Dict[str, Any]:
        steps = []
        try:
            rt = self._runtime
            status = rt.get_memory().get_stats()
            steps.append(f"memory_check: {status}")
            self._notifier.notify_recovery(failure_reason, " | ".join(steps) or "no_recovery_steps")
        except Exception as exc:
            steps.append(f"recovery_failed: {exc}")
        action = " | ".join(steps) or "no_recovery_steps"
        return {"status": "recovery_attempted", "reason": failure_reason, "steps": steps, "notification": "sent"}

