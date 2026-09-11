"""媒体类型扩展名与导入映射（单一事实源）。

类型 → 扩展名用表查找，禁止在调用处 if/else 硬编码。
桌面对话框扩展名须与本表去点后对齐：`domain/mediaTypes.ts`。
"""

from __future__ import annotations

from app.shared.models import ResourceType

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".avif"}
)
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts", ".m4v"}
)
SUBTITLE_EXTENSIONS: frozenset[str] = frozenset({".srt", ".ass", ".ssa", ".vtt"})

COVER_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS

IMPORT_EXTENSIONS: dict[ResourceType, frozenset[str]] = {
    ResourceType.IMAGE: IMAGE_EXTENSIONS,
    ResourceType.VIDEO: VIDEO_EXTENSIONS,
}

FILE_ROLE_PRIMARY = "primary"
FILE_ROLE_COVER = "cover"
FILE_ROLE_SUBTITLE = "subtitle"

FFPROBE_BIN = "ffprobe"
FFPROBE_TIMEOUT_SEC = 30

SUBTITLE_LANGUAGE_TAGS: frozenset[str] = frozenset(
    {
        "zh",
        "en",
        "ja",
        "ko",
        "fr",
        "de",
        "es",
        "ru",
        "pt",
        "it",
        "ar",
        "hi",
        "th",
        "vi",
        "id",
        "ms",
        "cht",
        "chs",
        "chi",
        "jpn",
        "kor",
        "und",
        "cc",
        "sc",
        "tc",
        "zh-cn",
        "zh-hans",
        "zh-hant",
        "zh-tw",
        "en-us",
        "en-gb",
    }
)


def import_extensions(type_: ResourceType) -> frozenset[str] | None:
    """导入候选扩展名；未登记的类型返回 None。"""
    return IMPORT_EXTENSIONS.get(type_)
