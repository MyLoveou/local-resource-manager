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
    ResourceType.ANIME: VIDEO_EXTENSIONS,
    ResourceType.AV: VIDEO_EXTENSIONS,
}

SERIES_TYPES: frozenset[ResourceType] = frozenset({ResourceType.ANIME, ResourceType.AV})
VIDEO_PROBE_TYPES: frozenset[ResourceType] = frozenset(
    {ResourceType.VIDEO, ResourceType.ANIME, ResourceType.AV}
)

FILE_ROLE_PRIMARY = "primary"
FILE_ROLE_COVER = "cover"
FILE_ROLE_SUBTITLE = "subtitle"
FILE_ROLE_THUMBNAIL = "thumbnail"
FILE_ROLE_EPISODE = "episode"
FILE_ROLE_EXTRA = "extra"

# 特典目录名（NCOP&NCED 按 & 切开后查表）。对齐 Anitomy 的 type 关键字，不是盘点每家字幕组。
SERIES_EXTRA_DIR_MARKERS: frozenset[str] = frozenset(
    {
        "特典",
        "映像特典",
        "特典映像",
        "extra",
        "extras",
        "special",
        "specials",
        "menu",
        "menus",
        "pv",
        "ncop",
        "nced",
        "tokuten",
        "cm",
        "credit",
        "credits",
    }
)
SERIES_EXTRA_TOKENS: frozenset[str] = frozenset(
    {
        "menu",
        "pv",
        "nced",
        "ncop",
        "tokuten",
        "cm",
        "sp",
        "special",
        "specials",
        "extra",
        "extras",
        "特典",
    }
)
SERIES_EXTRA_TOKEN_PREFIXES: tuple[str, ...] = (
    "nced",
    "ncop",
    "menu",
    "pv",
    "cm",
    "sp",
    "nc",
)


def is_series_type(type_: ResourceType) -> bool:
    """番剧/AV 按作品进库。"""
    return type_ in SERIES_TYPES

THUMB_DIR = "thumbs"
THUMB_GRID_NAME = "grid.webp"
THUMB_MAX_EDGE_PX = 480
THUMB_WEBP_QUALITY = 80

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
