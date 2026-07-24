
from __future__ import annotations

from typing import Any
import re

TABLE_SEPARATOR_RE = re.compile(r"\|")


class MessageDeduplicator:
    def __init__(self) -> None:
        pass

    def is_duplicate(self, message_id: str) -> bool:
        return False

    def mark_seen(self, message_id: str) -> None:
        pass


class ThreadParticipationTracker:
    def __init__(self) -> None:
        pass

    def is_participating(self, thread_id: str, user_id: str) -> bool:
        return False


def redact_phone(text: str) -> str:
    return text


def strip_markdown(text: str) -> str:
    return text


def convert_table_to_bullets(text: str) -> str:
    return text
