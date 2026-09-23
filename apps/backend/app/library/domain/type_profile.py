"""类型能力目录（编译期 TypeProfile，不是表）。

调用方查表，禁止用类型字面量选过滤表、播放器或是否复制。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.shared.models import ResourceType, StorageKind

IngestKind = Literal["file", "series", "package", "directory"]
ConsumeKind = Literal[
    "overlay-image",
    "overlay-video",
    "overlay-audio",
    "overlay-series",
    "overlay-model",
    "shell-open",
]
PackageContents = Literal["launch_tree", "image_pages"]

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".avif"}
)
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts", ".m4v"}
)
AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma", ".opus"}
)
NOVEL_EXTENSIONS: frozenset[str] = frozenset(
    {".epub", ".pdf", ".txt", ".html", ".htm", ".mobi", ".azw3"}
)
GAME_LAUNCH_EXTENSIONS: frozenset[str] = frozenset({".exe", ".bat", ".cmd", ".lnk"})
MODEL_EXTENSIONS: frozenset[str] = frozenset({".gltf", ".glb", ".obj", ".fbx", ".stl"})
MODEL_PREVIEW_EXTENSIONS: frozenset[str] = frozenset({".gltf", ".glb"})
COMIC_ARCHIVE_EXTENSIONS: frozenset[str] = frozenset({".cbz", ".cbr"})
COMIC_EXTENSIONS: frozenset[str] = IMAGE_EXTENSIONS | COMIC_ARCHIVE_EXTENSIONS


@dataclass(frozen=True)
class TypeProfile:
    """一种库类型怎么进、怎么列、怎么开、文件落在哪。"""

    type: ResourceType
    label: str
    empty_hint: str
    route_path: str
    route_icon: str
    ingest_kind: IngestKind
    consume_kind: ConsumeKind
    default_source: Literal["file", "directory"]
    default_storage: StorageKind
    allowed_storage: frozenset[StorageKind]
    extensions: frozenset[str]
    cover_fallback: bool
    allows_file_source: bool
    package_contents: PackageContents | None = None
    enabled: bool = True
    search_keys: frozenset[str] = frozenset()
    sort_keys: frozenset[str] = frozenset()
    allows_user_cover: bool = True


_OWNED = frozenset({StorageKind.OWNED})
_GAME_STORAGE = frozenset({StorageKind.INDEXED, StorageKind.OWNED})

TYPE_PROFILES: tuple[TypeProfile, ...] = (
    TypeProfile(
        ResourceType.IMAGE,
        "图片",
        "暂无图片，请先在顶栏导入",
        "/image",
        "image",
        "file",
        "overlay-image",
        "file",
        StorageKind.OWNED,
        _OWNED,
        IMAGE_EXTENSIONS,
        True,
        True,
        search_keys=frozenset({"format"}),
        sort_keys=frozenset({"width", "height", "pixelArea", "takenAt"}),
        allows_user_cover=False,
    ),
    TypeProfile(
        ResourceType.VIDEO,
        "视频",
        "暂无视频，请先在顶栏导入",
        "/video",
        "video",
        "file",
        "overlay-video",
        "file",
        StorageKind.OWNED,
        _OWNED,
        VIDEO_EXTENSIONS,
        False,
        True,
        search_keys=frozenset({"format"}),
        sort_keys=frozenset({"duration", "resolution", "bitrate"}),
    ),
    TypeProfile(
        ResourceType.ANIME,
        "番剧",
        "暂无番剧，请先在顶栏导入文件夹",
        "/anime",
        "anime",
        "series",
        "overlay-series",
        "directory",
        StorageKind.OWNED,
        _OWNED,
        VIDEO_EXTENSIONS,
        True,
        False,
        sort_keys=frozenset({"episodeCount"}),
    ),
    TypeProfile(
        ResourceType.AV,
        "AV",
        "暂无 AV，请先在顶栏导入文件夹",
        "/av",
        "av",
        "series",
        "overlay-series",
        "directory",
        StorageKind.OWNED,
        _OWNED,
        VIDEO_EXTENSIONS,
        True,
        False,
        sort_keys=frozenset({"episodeCount"}),
    ),
    TypeProfile(
        ResourceType.AUDIO,
        "音频",
        "暂无音频，请先在顶栏导入",
        "/audio",
        "music",
        "file",
        "overlay-audio",
        "file",
        StorageKind.OWNED,
        _OWNED,
        AUDIO_EXTENSIONS,
        False,
        True,
        search_keys=frozenset({"format"}),
        sort_keys=frozenset({"duration"}),
    ),
    TypeProfile(
        ResourceType.NOVEL,
        "小说",
        "暂无小说，请先在顶栏导入",
        "/novel",
        "book-open-page-variant",
        "file",
        "shell-open",
        "file",
        StorageKind.OWNED,
        _OWNED,
        NOVEL_EXTENSIONS,
        False,
        True,
    ),
    TypeProfile(
        ResourceType.GAME,
        "游戏",
        "暂无游戏，请先在顶栏导入文件夹",
        "/game",
        "controller-classic",
        "package",
        "shell-open",
        "directory",
        StorageKind.INDEXED,
        _GAME_STORAGE,
        GAME_LAUNCH_EXTENSIONS,
        False,
        False,
        "launch_tree",
        search_keys=frozenset({"path"}),
    ),
    TypeProfile(
        ResourceType.MODEL,
        "模型",
        "暂无模型，请先在顶栏导入",
        "/model",
        "cube-outline",
        "file",
        "overlay-model",
        "file",
        StorageKind.OWNED,
        _OWNED,
        MODEL_EXTENSIONS,
        False,
        True,
        search_keys=frozenset({"format"}),
    ),
    TypeProfile(
        ResourceType.COMIC,
        "漫画",
        "暂无漫画，请先在顶栏导入文件夹",
        "/comic",
        "book-open-blank-variant",
        "package",
        "shell-open",
        "directory",
        StorageKind.OWNED,
        _OWNED,
        COMIC_EXTENSIONS,
        True,
        True,
        "image_pages",
        sort_keys=frozenset({"pageCount"}),
    ),
    TypeProfile(
        ResourceType.WORK_DIRECTORY,
        "工作目录",
        "暂无工作目录，点上方添加本地文件夹",
        "/work",
        "folder-outline",
        "directory",
        "shell-open",
        "directory",
        StorageKind.INDEXED,
        frozenset({StorageKind.INDEXED}),
        frozenset(),
        False,
        False,
        allows_user_cover=False,
    ),
)

_BY_TYPE: dict[ResourceType, TypeProfile] = {p.type: p for p in TYPE_PROFILES if p.enabled}

IMPORT_EXTENSIONS: dict[ResourceType, frozenset[str]] = {
    p.type: p.extensions for p in TYPE_PROFILES if p.enabled
}
SERIES_TYPES: frozenset[ResourceType] = frozenset(
    p.type for p in TYPE_PROFILES if p.ingest_kind == "series"
)
VIDEO_PROBE_TYPES: frozenset[ResourceType] = frozenset(
    {ResourceType.VIDEO, ResourceType.ANIME, ResourceType.AV}
)
AUDIO_PROBE_TYPES: frozenset[ResourceType] = frozenset({ResourceType.AUDIO})


def profile_for(type_: ResourceType) -> TypeProfile | None:
    """已启用档案；未登记则 None。"""
    return _BY_TYPE.get(type_)


def ingest_kind(type_: ResourceType) -> IngestKind | None:
    profile = profile_for(type_)
    return None if profile is None else profile.ingest_kind


def consume_kind(type_: ResourceType) -> ConsumeKind | None:
    profile = profile_for(type_)
    return None if profile is None else profile.consume_kind


def storage_allowed(type_: ResourceType, kind: StorageKind) -> bool:
    profile = profile_for(type_)
    return profile is not None and kind in profile.allowed_storage


def is_series_type(type_: ResourceType) -> bool:
    """番剧/AV 按作品进库。"""
    return type_ in SERIES_TYPES


def is_package_type(type_: ResourceType) -> bool:
    return ingest_kind(type_) == "package"


def import_extensions(type_: ResourceType) -> frozenset[str] | None:
    """导入候选扩展名；未登记的类型返回 None。"""
    return IMPORT_EXTENSIONS.get(type_)


def allows_user_cover(type_: ResourceType) -> bool:
    """除图片外可手选封面。"""
    profile = profile_for(type_)
    return profile is not None and profile.allows_user_cover
