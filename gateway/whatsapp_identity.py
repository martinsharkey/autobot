
from __future__ import annotations

from typing import Any


def to_whatsapp_jid(phone: str) -> str:
    return f"{phone}@s.whatsapp.net"
