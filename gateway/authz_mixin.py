
from __future__ import annotations

from typing import Any, Optional


class AuthorizationMixin:
    def is_authorized(self, user_id: str, permission: str) -> bool:
        return False

    def get_permissions(self, user_id: str) -> list[str]:
        return []


def _coerce_allow_set(value: Any) -> set[str]:
    if isinstance(value, set):
        return value
    if isinstance(value, list):
        return set(value)
    if isinstance(value, str):
        return {value}
    return set()
