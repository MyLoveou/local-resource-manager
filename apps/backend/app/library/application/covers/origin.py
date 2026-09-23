"""封面来源标记。存在 extra.coverOrigin，与其它 extra 键合并。"""

from __future__ import annotations

from typing import Any

from app.shared.models import Resource

COVER_ORIGIN_USER = "user"
COVER_ORIGIN_FOLDER = "folder"
COVER_ORIGIN_FRAME = "frame"
COVER_ORIGIN_EXE = "exe"
COVER_ORIGIN_PAGE = "page"
COVER_ORIGIN_EMBEDDED = "embedded"
COVER_ORIGIN_SCRAPED = "scraped"


class CoverNotAllowedError(ValueError):
    """图片等类型禁止手换封面。"""

    def __init__(self) -> None:
        super().__init__("cover not allowed")


def merge_cover_origin(extra: dict[str, Any] | None, origin: str) -> dict[str, Any]:
    merged = dict(extra or {})
    merged["coverOrigin"] = origin
    return merged


def is_user_locked(resource: Resource) -> bool:
    extra = resource.extra or {}
    return extra.get("coverOrigin") == COVER_ORIGIN_USER
