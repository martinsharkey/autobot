
from __future__ import annotations

from typing import Any


def build_session_key(session_id: str, user_id: str = "") -> str:
    return session_key


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}

    def create(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        self._sessions[session_id] = kwargs
        return kwargs

    def get(self, session_id: str) -> dict[str, Any]:
        return self._sessions.get(session_id, {})


session_manager = SessionManager()
