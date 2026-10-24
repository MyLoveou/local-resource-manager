"""资源库应用 · 领域实体。

库内资源聚合及其附属：文件/标签/分类/待办/季集树/站点档案。
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.shared.errors import InvalidStateError
from app.shared.models import ApiModel
from app.shared.value_objects import Dimension, Rating


class ResourceType(str, Enum):
    """资源类型。anime/av 是作品行，不是单集文件。"""

    IMAGE = "image"
    VIDEO = "video"
    ANIME = "anime"
    AV = "av"
    AUDIO = "audio"
    NOVEL = "novel"
    GAME = "game"
    MODEL = "model"
    COMIC = "comic"
    WORK_DIRECTORY = "work_directory"


class StorageKind(str, Enum):
    """文件落盘：库内副本 / 源路径登记。"""

    OWNED = "owned"
    INDEXED = "indexed"


class ResourceStatus(str, Enum):
    """资源状态：正常 / 回收站（软删）/ 文件丢失。"""

    ACTIVE = "active"
    TRASHED = "trashed"
    LOST = "lost"


class SeriesEpisode(ApiModel):
    """一集：挂在季下，指向 files 行，本身不是 Resource。"""

    id: int | None = None
    file_id: int
    episode_number: int
    title: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None


class SeriesSeason(ApiModel):
    """一季。"""

    id: int | None = None
    season_number: int
    title: str | None = None
    episodes: list[SeriesEpisode] = Field(default_factory=list)


class SeriesExtra(ApiModel):
    """特典：挂在作品下，不计入正片集数。"""

    id: int | None = None
    file_id: int
    title: str = ""
    duration: float | None = None


class WorkCatalog(ApiModel):
    """站点作品档案（刮削写入）。用户评价在 description，用户评分在 rating。"""

    original_title: str | None = None
    name_cn: str | None = None
    date: str | None = None
    platform: str | None = None
    eps: int | None = None
    total_episodes: int | None = None
    site_score: float | None = None
    infobox: list[dict[str, Any]] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    source: str | None = None
    source_id: str | None = None


class PersonBrief(ApiModel):
    id: int
    name: str


class Person(ApiModel):
    id: int | None = None
    name: str
    description: str | None = None
    cover_resource_id: int | None = None
    cover_path: str | None = None
    aliases: list[str] = Field(default_factory=list)
    resource_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CharacterBrief(ApiModel):
    id: int
    name: str
    work_id: int | None = None
    work_name: str | None = None


class Character(ApiModel):
    id: int | None = None
    name: str
    work_id: int | None = None
    work_name: str | None = None
    description: str | None = None
    cover_resource_id: int | None = None
    cover_path: str | None = None
    aliases: list[str] = Field(default_factory=list)
    resource_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Work(ApiModel):
    id: int | None = None
    name: str
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Resource(ApiModel):
    """库内一条资源。图片/视频是单文件作品；anime/av 是整部作品，集在 seasons/episodes。"""

    id: int | None = None
    type: ResourceType
    storage_kind: StorageKind = StorageKind.OWNED
    title: str = ""
    description: str | None = None  # 用户对作品的评价/笔记
    synopsis: str | None = None  # 作品简介（刮削/站点）
    catalog: WorkCatalog | None = None  # 站点档案（番剧等）
    author: str | None = None
    rating: Rating | None = None  # 评分 0-10（约束类型值对象）
    cover_path: str | None = None  # 封面本地缓存路径（原图，信息栏用）
    thumbnail_path: str | None = None  # 网格缩略图 content URL，不是 cover_path
    status: ResourceStatus = ResourceStatus.ACTIVE
    deleted_at: datetime | None = None  # 回收站删除时间
    last_scraped_at: datetime | None = None  # 上次元数据抓取时间
    scraped_source: str | None = None  # 抓取来源站点（审计）
    extra: dict[str, Any] = Field(default_factory=dict)  # 站点特有元数据兜底
    scrape_pending: bool = False  # 有未确认的 search 候选
    timeline_visible: bool | None = None  # 照片时间线：None=按 EXIF 自动
    map_visible: bool | None = None  # 地图：None=有 GPS 自动纳入
    characters: list[CharacterBrief] = Field(default_factory=list)
    persons: list[PersonBrief] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    categories: list["Category"] = Field(default_factory=list)
    tags: list["Tag"] = Field(default_factory=list)
    files: list["ResourceFile"] = Field(default_factory=list)
    todos: list["ResourceTodo"] = Field(default_factory=list)
    seasons: list[SeriesSeason] = Field(default_factory=list)
    extras: list[SeriesExtra] = Field(default_factory=list)

    @property
    def is_trashed(self) -> bool:
        """是否在回收站。"""
        return self.status == ResourceStatus.TRASHED

    @property
    def is_lost(self) -> bool:
        """文件是否丢失。"""
        return self.status == ResourceStatus.LOST

    def to_trash(self) -> None:
        """移入回收站（软删除）。任意非回收站状态均可进入。"""
        self.status = ResourceStatus.TRASHED
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """从回收站恢复。仅 trashed 状态合法。"""
        if not self.is_trashed:
            raise InvalidStateError(f"cannot restore resource in status {self.status}")
        self.status = ResourceStatus.ACTIVE
        self.deleted_at = None
        self._touch()

    def mark_lost(self) -> None:
        """标记文件丢失。仅 active 状态合法。"""
        if self.status != ResourceStatus.ACTIVE:
            raise InvalidStateError(f"cannot mark lost from status {self.status}")
        self.status = ResourceStatus.LOST
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now()


class ResourceFile(ApiModel):
    """资源关联的物理文件。一个资源可含多文件（如视频+字幕）。"""

    id: int | None = None
    resource_id: int
    path: str
    sha256: str | None = None  # 文件哈希，图片元数据匹配键（唯一索引）
    size: int | None = None
    format: str | None = None  # 扩展名/格式
    role: str = "primary"  # primary / cover / subtitle / thumbnail
    duration: float | None = None  # 视频时长（秒）
    width: int | None = None
    height: int | None = None
    codec: str | None = None  # 视频编码
    fps: float | None = None
    bitrate: int | None = None  # 比特/秒
    exif_taken_at: str | None = None  # 图片拍摄时间 ISO 本地日历
    exif_lat: float | None = None  # WGS84 纬度
    exif_lng: float | None = None  # WGS84 经度
    exif_camera: str | None = None  # 机身 Make+Model
    exif_lens: str | None = None
    exif_iso: int | None = None
    exif_aperture: str | None = None  # 如 f/2.8
    exif_shutter: str | None = None  # 如 1/125
    created_at: datetime | None = None

    @property
    def dimension(self) -> Dimension | None:
        """宽高值对象（只读视图）。"""
        if self.width is not None and self.height is not None:
            return Dimension(width=self.width, height=self.height)
        return None

    @property
    def aspect_ratio(self) -> float | None:
        """宽高比（由 Dimension 值对象计算）。"""
        dim = self.dimension
        return dim.aspect_ratio if dim else None

    def matches_hash(self, sha256: str) -> bool:
        """是否为指定哈希的文件（图片元数据匹配键）。"""
        return self.sha256 is not None and self.sha256.lower() == sha256.lower()


class ResourceTodo(ApiModel):
    """挂在单条资源上的待办。"""

    id: int | None = None
    resource_id: int
    content: str
    done: bool = False
    sort: int = 0
    created_at: datetime | None = None


class Tag(ApiModel):
    """标签词条。"""

    id: int | None = None
    name: str


class Category(ApiModel):
    """分类词表；每个资源类型一棵独立树。"""

    id: int | None = None
    name: str
    type: ResourceType | None = None
    parent_id: int | None = None
    sort: int = 0
    is_system: bool = False


class CategoryRule(ApiModel):
    include: list[int] = Field(default_factory=list)
    exclude: list[int] = Field(default_factory=list)


class SavedViewFilters(ApiModel):
    """时间线规则：图片/视频各自包含与排除；无成员表。"""

    image: CategoryRule = Field(default_factory=CategoryRule)
    video: CategoryRule = Field(default_factory=CategoryRule)
    tag_ids: list[int] = Field(default_factory=list)
    character_ids: list[int] = Field(default_factory=list)
    person_ids: list[int] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    include_untimed: bool = False


class SavedView(ApiModel):
    id: int | None = None
    kind: str = "timeline"
    scope: str = "image"  # image / video / media
    name: str
    filters: SavedViewFilters = Field(default_factory=SavedViewFilters)
    sort: str = "takenAt"
    created_at: str | None = None
    updated_at: str | None = None


class TimelineNote(ApiModel):
    """时间线备注：全局日期备注，或某条保存时间线备注。"""

    id: int | None = None
    scope: str  # date / saved_view
    date: str | None = None
    saved_view_id: int | None = None
    title: str = ""
    body: str | None = None
    location_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Collection(ApiModel):
    """合集：用户手动把资源组成一组（可跨类型、可排序）。"""

    id: int | None = None
    title: str
    description: str | None = None
    member_count: int = 0  # active 成员数，列表展示用
    preview_thumbnails: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class CollectionItem(ApiModel):
    """合集成员（resourceId 引用 + 手动顺序）。"""

    collection_id: int
    resource_id: int
    position: int = 0


class SourceKind(str, Enum):
    """导入来源：文件或多文件 / 一次选目录。"""

    FILE = "file"
    DIRECTORY = "directory"


HIDDEN_NAME_PREFIX = "."


def is_hidden_fs_name(name: str) -> bool:
    """点开头的文件或目录不参与导入收集。"""
    return name.startswith(HIDDEN_NAME_PREFIX)
