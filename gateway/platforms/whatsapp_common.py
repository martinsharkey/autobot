
from __future__ import annotations

from typing import Any


class WhatsAppBehaviorMixin:
    def should_show_typing_indicator(self) -> bool:
        return False
