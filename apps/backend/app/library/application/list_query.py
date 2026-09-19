"""列表查询：共用搜排键、LIKE 转义、sort 白名单。"""

from __future__ import annotations

from app.library.domain.type_profile import profile_for
from app.shared.models import ResourceType

SHARED_SORT: frozenset[str] = frozenset({"createdAt", "updatedAt", "title", "rating", "size"})
CLARITY_PX: frozenset[int] = frozenset({480, 720, 1080, 1440, 2160, 4320})
NULL_CURSOR = "__null__"
MAX_Q = 200


def escape_like(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def normalize_q(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    return text[:MAX_Q]


def like_pattern(q: str) -> str:
    return f"%{escape_like(q.lower())}%"


def allowed_sorts(type_: ResourceType | None) -> frozenset[str]:
    if type_ is None:
        return SHARED_SORT
    profile = profile_for(type_)
    extra = profile.sort_keys if profile is not None else frozenset()
    return SHARED_SORT | extra


def serialize_sort_value(value: object) -> str:
    if value is None:
        return NULL_CURSOR
    return str(value)


def parse_sort_value(raw: str) -> object:
    if raw == NULL_CURSOR:
        return None
    return raw
