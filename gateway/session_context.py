
from __future__ import annotations

from typing import Any, Dict, List, Optional


def session_context_engaged() -> bool:
    return False


def set_current_session_id(session_id: str) -> None:
    pass


def set_session_vars(
    session_id: str,
    platform: str = "",
    channel: str = "",
    user_id: str = "",
) -> None:
    pass


def clear_session_vars(tokens: list) -> None:
    pass


def reset_session_vars() -> None:
    pass


def get_session_env(name: str, default: str = "") -> str:
    return default


def declare_stateless_channel() -> None:
    pass


def async_delivery_supported() -> bool:
    return False


def get_current_session_id() -> Optional[str]:
    return None


def get_session_platform() -> Optional[str]:
    return None


class SessionContext:
    def __init__(self) -> None:
        self.session_id: Optional[str] = None
        self.platform: Optional[str] = None
        self.channel: Optional[str] = None
        self.user_id: Optional[str] = None
        self._vars: Dict[str, str] = {}

    def engage(self, session_id: str) -> None:
        self.session_id = session_id

    def set(self, key: str, value: str) -> None:
        self._vars[key] = value

    def get(self, key: str, default: str = "") -> str:
        return self._vars.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "platform": self.platform,
            "channel": self.channel,
            "user_id": self.user_id,
            "vars": dict(self._vars),
        }


_session_ctx = SessionContext()


def get_context() -> SessionContext:
    return _session_ctx
