"""媒体类型扩展名与导入映射（单一事实源）。

类型档案见 `app.library.domain.type_profile`。本模块再导出扩展名与角色常量，避免调用方大爆炸。
"""

from __future__ import annotations

from app.library.domain.type_profile import (
    AUDIO_EXTENSIONS,
    AUDIO_PROBE_TYPES,
    COMIC_ARCHIVE_EXTENSIONS,
    COMIC_EXTENSIONS,
    GAME_LAUNCH_EXTENSIONS,
    IMAGE_EXTENSIONS,
    IMPORT_EXTENSIONS,
    MODEL_EXTENSIONS,
    MODEL_PREVIEW_EXTENSIONS,
    NOVEL_EXTENSIONS,
    SERIES_TYPES,
    VIDEO_EXTENSIONS,
    VIDEO_PROBE_TYPES,
    consume_kind,
    import_extensions,
    ingest_kind,
    is_package_type,
    is_series_type,
    profile_for,
    storage_allowed,
)

COVER_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS
SUBTITLE_EXTENSIONS: frozenset[str] = frozenset({".srt", ".ass", ".ssa", ".vtt"})

FILE_ROLE_PRIMARY = "primary"
FILE_ROLE_COVER = "cover"
FILE_ROLE_SUBTITLE = "subtitle"
FILE_ROLE_THUMBNAIL = "thumbnail"
FILE_ROLE_PREVIEW = "preview"
FILE_ROLE_EPISODE = "episode"
FILE_ROLE_EPISODE_COVER = "episode_cover"
FILE_ROLE_EXTRA = "extra"
FILE_ROLE_LAUNCH = "launch"
FILE_ROLE_PAGE = "page"

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

THUMB_DIR = "thumbs"
THUMB_GRID_NAME = "grid.webp"
THUMB_MAX_EDGE_PX = 480
THUMB_WEBP_QUALITY = 80
PREVIEW_NAME = "preview.jpg"

FFPROBE_BIN = "ffprobe"
FFPROBE_TIMEOUT_SEC = 30
FFMPEG_BIN = "ffmpeg"
FFMPEG_TIMEOUT_SEC = 30

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

__all__ = [
    "AUDIO_EXTENSIONS",
    "AUDIO_PROBE_TYPES",
    "COMIC_ARCHIVE_EXTENSIONS",
    "COMIC_EXTENSIONS",
    "COVER_EXTENSIONS",
    "FFPROBE_BIN",
    "FFPROBE_TIMEOUT_SEC",
    "FILE_ROLE_COVER",
    "FILE_ROLE_EPISODE",
    "FILE_ROLE_EPISODE_COVER",
    "FILE_ROLE_EXTRA",
    "FILE_ROLE_LAUNCH",
    "FILE_ROLE_PAGE",
    "FILE_ROLE_PRIMARY",
    "FILE_ROLE_SUBTITLE",
    "FILE_ROLE_THUMBNAIL",
    "GAME_LAUNCH_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "IMPORT_EXTENSIONS",
    "MODEL_EXTENSIONS",
    "MODEL_PREVIEW_EXTENSIONS",
    "NOVEL_EXTENSIONS",
    "SERIES_EXTRA_DIR_MARKERS",
    "SERIES_EXTRA_TOKENS",
    "SERIES_EXTRA_TOKEN_PREFIXES",
    "SERIES_TYPES",
    "SUBTITLE_EXTENSIONS",
    "SUBTITLE_LANGUAGE_TAGS",
    "THUMB_DIR",
    "THUMB_GRID_NAME",
    "THUMB_MAX_EDGE_PX",
    "THUMB_WEBP_QUALITY",
    "VIDEO_EXTENSIONS",
    "VIDEO_PROBE_TYPES",
    "consume_kind",
    "import_extensions",
    "ingest_kind",
    "is_package_type",
    "is_series_type",
    "profile_for",
    "storage_allowed",
]
