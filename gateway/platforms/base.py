from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    PHOTO = "photo"
    STICKER = "sticker"
    VOICE = "voice"
    DOCUMENT = "document"
    LOCATION = "location"


class ProcessingOutcome:
    ACCEPT = "accept"
    REJECT = "reject"
    REDIRECT = "redirect"


@dataclass
class MessageEvent:
    text: str
    user_id: str = ""
    platform: str = "web"
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SendResult:
    success: bool
    message_id: str = ""
    error: str = ""


class BasePlatformAdapter:
    def __init__(self, **kwargs: Any) -> None:
        pass

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def send_message(self, text: str, **kwargs: Any) -> SendResult:
        return SendResult(success=True)

    def parse_event(self, raw: Dict[str, Any]) -> MessageEvent:
        return MessageEvent(text=raw.get("text", ""), user_id=raw.get("user_id", ""), platform=raw.get("platform", "web"))


def should_send_media_as_audio(platform: str, media_type: str) -> bool:
    return False


SUPPORTED_IMAGE_DOCUMENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp"
}
SUPPORTED_VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska"
}
SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".csv": "text/csv"
}


def cache_document_from_bytes(data: bytes, content_type: str) -> str:
    return ""


def cache_image_from_bytes(data: bytes, content_type: str) -> str:
    return ""


def cache_audio_from_bytes(data: bytes, content_type: str) -> str:
    return ""


def cache_video_from_bytes(data: bytes, content_type: str) -> str:
    return ""


def cache_audio_from_url(url: str) -> str:
    return ""


def cache_video_from_url(url: str) -> str:
    return ""


def cache_image_from_url(url: str) -> str:
    return ""


def cache_document_from_url(url: str) -> str:
    return ""


_ssrf_redirect_guard = None
_TEXT_INJECT_EXTENSIONS = ()

def cache_media_bytes(data: bytes, content_type: str) -> str:
    return ""


def resolve_proxy_url(original_url: str) -> str:
    return original_url


def utf16_len(s: str) -> int:
    return len(s)


def _prefix_within_utf16_limit(s: str, limit: int) -> str:
    return s[:limit]


def is_host_excluded_by_no_proxy(host: str) -> bool:
    return False


def proxy_kwargs_for_aiohttp(original_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return original_kwargs


def classify_send_error(exc: Exception) -> str:
    return "unknown_error"


def merge_pending_message_event(base: MessageEvent, override: MessageEvent) -> MessageEvent:
    return override
