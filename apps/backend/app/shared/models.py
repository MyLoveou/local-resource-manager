"""共享领域模型（跨抓取/下载子应用的通用实体）。

契约约定：
- 数据库字段用 snake_case
- API JSON 序列化为 camelCase（对齐前端 TS 类型）
- 通过 `ApiModel` 统一实现，新增模型继承它即可
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.shared.constants import AdapterKey
from app.shared.errors import InvalidStateError
from app.shared.value_objects import Dimension, Rating


class ApiModel(BaseModel):
    """API 契约基类：snake_case 字段 ↔ camelCase JSON。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


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


class Resource(ApiModel):
    """库内一条资源。图片/视频是单文件作品；anime/av 是整部作品，集在 seasons/episodes。"""

    id: int | None = None
    type: ResourceType
    storage_kind: StorageKind = StorageKind.OWNED
    title: str = ""
    description: str | None = None
    author: str | None = None
    rating: Rating | None = None  # 评分 0-10（约束类型值对象）
    cover_path: str | None = None  # 封面本地缓存路径（原图，信息栏用）
    thumbnail_path: str | None = None  # 网格缩略图 content URL，不是 cover_path
    status: ResourceStatus = ResourceStatus.ACTIVE
    deleted_at: datetime | None = None  # 回收站删除时间
    last_scraped_at: datetime | None = None  # 上次元数据抓取时间
    scraped_source: str | None = None  # 抓取来源站点（审计）
    extra: dict[str, Any] = Field(default_factory=dict)  # 站点特有元数据兜底
    created_at: datetime | None = None
    updated_at: datetime | None = None
    category: "Category | None" = None
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
    exif_taken_at: datetime | None = None  # 图片拍摄时间（EXIF）
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
    """分类词条（资源单选）。"""

    id: int | None = None
    name: str


class Settings(ApiModel):
    """应用设置（KV 结构）。"""

    key: str
    value: dict[str, Any]


class SiteAdapter(ApiModel):
    """站点适配器配置（插件式）。key 为常量枚举 AdapterKey。"""

    id: int | None = None
    key: AdapterKey
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
