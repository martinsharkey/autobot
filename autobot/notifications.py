
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class NotificationClient:
    def __init__(self) -> None:
        self._telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self._whatsapp_token = os.getenv("WHATSAPP_TOKEN", "")
        self._whatsapp_phone = os.getenv("WHATSAPP_PHONE", "")
        self._whatsapp_recipient = os.getenv("WHATSAPP_RECIPIENT", "")

    def send_telegram(self, text: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
        if not self._telegram_token:
            return {"status": "skipped", "reason": "no_telegram_token"}
        target = chat_id or self._telegram_chat_id
        if not target:
            return {"status": "skipped", "reason": "no_telegram_chat_id"}
        try:
            resp = httpx.post(
                f"https://api.telegram.org/bot{self._telegram_token}/sendMessage",
                json={"chat_id": target, "text": text},
                timeout=15,
            )
            data = resp.json()
            return {"status": "ok" if data.get("ok") else "failed", "response": data}
        except Exception as exc:
            logger.warning("telegram send failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def send_whatsapp(self, text: str, recipient: Optional[str] = None) -> Dict[str, Any]:
        if not self._whatsapp_token or not self._whatsapp_phone:
            return {"status": "skipped", "reason": "no_whatsapp_credentials"}
        target = recipient or self._whatsapp_recipient
        if not target:
            return {"status": "skipped", "reason": "no_whatsapp_recipient"}
        try:
            resp = httpx.post(
                f"https://graph.facebook.com/v18.0/{self._whatsapp_phone}/messages",
                headers={"Authorization": f"Bearer {self._whatsapp_token}", "Content-Type": "application/json"},
                json={
                    "messaging_product": "whatsapp",
                    "to": target,
                    "type": "text",
                    "text": {"body": text},
                },
                timeout=15,
            )
            data = resp.json()
            return {"status": "ok" if data.get("messages") else "failed", "response": data}
        except Exception as exc:
            logger.warning("whatsapp send failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def notify(self, text: str, priority: str = "normal") -> Dict[str, Any]:
        results = {
            "telegram": self.send_telegram(text),
            "whatsapp": self.send_whatsapp(text),
        }
        return {"priority": priority, "channels": results}

    def notify_autonomy_milestone(self, milestone: str, detail: str = "") -> Dict[str, Any]:
        text = f"AUTOBOT Autonomy Milestone: {milestone}\n{detail}".strip()
        return self.notify(text, priority="high")

    def notify_recovery(self, reason: str, action_taken: str) -> Dict[str, Any]:
        text = f"AUTOBOT Recovery: {reason}\nAction: {action_taken}"
        return self.notify(text, priority="high")

    def notify_full_autonomy(self) -> Dict[str, Any]:
        text = "AUTOBOT Full Autonomy Achieved.\nAll readiness gates passed. Operating autonomously."
        return self.notify(text, priority="critical")
