"""资源库应用 DTO（API 契约，继承 ApiModel 以输出 camelCase）。"""
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from app.library.domain.models import SourceKind
from app.shared.models import ApiModel
from app.library.domain.models import (
    Category,
    Resource,
    ResourceType,
    StorageKind,
    Tag,
)
from app.shared.value_objects import Rating


class ResourceStats(ApiModel):
    """资源统计。"""

    by_type: dict[str, int] = Field(default_factory=dict)
    total_size_bytes: int = 0
    trashed_count: int = 0
    lost_count: int = 0


class TaskSummary(ApiModel):
    """进行中任务概览。"""

    running_scrape_jobs: int = 0
    failed_scrape_jobs: int = 0
    active_downloads: int = 0


class ConsumptionItem(ApiModel):
    """一次打开/播放记录。"""

    id: int
    resource_id: int
    title: str
    type: str
    action: str
    created_at: str | None = None


class Overview(ApiModel):
    """首页概览（统计 + 最近添加 + 任务 + 工作）。"""

    stats: ResourceStats
    recent: list[Resource]
    tasks: TaskSummary
    active_work: list[Resource] = Field(default_factory=list)
    recent_consumption: list[ConsumptionItem] = Field(default_factory=list)


class ResourceSortField(str, Enum):
    """列表排序字段（JSON camelCase）。"""

    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
    TITLE = "title"
    RATING = "rating"
    SIZE = "size"
    WIDTH = "width"
    HEIGHT = "height"
    PIXEL_AREA = "pixelArea"
    TAKEN_AT = "takenAt"
    DURATION = "duration"
    RESOLUTION = "resolution"
    BITRATE = "bitrate"
    PAGE_COUNT = "pageCount"
    EPISODE_COUNT = "episodeCount"


class ResourcePage(ApiModel):
    """资源列表分页信封。全库混排时 items 含 Resource 与 CollectionCard。"""

    items: list[Any]
    total: int
    limit: int
    offset: int
    has_more: bool
    next_created_at: str | None = None
    next_id: int | None = None
    next_key: str | None = None


class CollectionCard(ApiModel):
    """全库混排里的合集卡。"""

    card_type: Literal["collection"] = "collection"
    id: int
    title: str
    member_count: int = 0
    updated_at: str | None = None


class CollectionCreate(ApiModel):
    title: str
    description: str | None = None


class CollectionPatch(ApiModel):
    title: str | None = None
    description: str | None = None


class CollectionOut(ApiModel):
    id: int
    title: str
    description: str | None = None
    member_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class CollectionList(ApiModel):
    items: list[CollectionOut]


class CollectionAddItem(ApiModel):
    resource_id: int


class CollectionMove(ApiModel):
    direction: Literal["up", "down"]


class ResourcePatch(ApiModel):
    """资源部分更新。tag_names 若出现则整表替换该资源标签；category_name 按名查找或创建分类。"""

    title: str | None = None
    description: str | None = None
    synopsis: str | None = None
    author: str | None = None
    rating: Rating | None = None
    category_name: str | None = None
    tag_names: list[str] | None = None
    exif_taken_at: str | None = None
    timeline_visible: bool | None = None


class PhotoTile(ApiModel):
    id: int
    title: str = ""
    kind: Literal["image", "video"] = "image"
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    thumbnail_path: str | None = None
    taken_at: str | None = None


class PhotoTimelineDay(ApiModel):
    date: str
    count: int
    photos: list[PhotoTile] = Field(default_factory=list)


class PhotoTimeline(ApiModel):
    days: list[PhotoTimelineDay] = Field(default_factory=list)
    unknown_count: int = 0
    unknown_photos: list[PhotoTile] = Field(default_factory=list)
    total: int = 0


class PhotoBackfillResult(ApiModel):
    scanned: int = 0
    taken_at_updated: int = 0
    gps_updated: int = 0
    skipped: int = 0
    failed: int = 0


class CoverReplace(ApiModel):
    """更换封面：本机已存在的图片路径。"""

    path: str


class SubtitleAdd(ApiModel):
    """添加字幕：本机已存在的字幕路径。"""

    path: str


class TodoCreate(ApiModel):
    """新增待办。"""

    content: str


class TodoPatch(ApiModel):
    """待办部分更新。"""

    content: str | None = None
    done: bool | None = None


class CategoryList(ApiModel):
    """分类词表只读列表。"""

    items: list[Category]


class TagList(ApiModel):
    """标签词表只读列表。"""

    items: list[Tag]


class ImportCreate(ApiModel):
    """创建导入任务。"""

    type: ResourceType
    source_kind: SourceKind
    paths: list[str] = Field(min_length=1)
    storage_kind: StorageKind | None = None
    timeline_visible: bool | None = None


class ImportJobCreated(ApiModel):
    """已接受的导入任务。"""

    job_id: str


class ResourceBatchRequest(ApiModel):
    """批量操作（移回收站/恢复/彻底删除/批量打标）；ids 去重后逐条处理，200 返回每项结果。"""

    action: Literal["trash", "restore", "purge", "add_tags"]
    ids: list[int] = Field(min_length=1, max_length=200)
    tag_names: list[str] | None = None


class CollectionExportRequest(ApiModel):
    target_dir: str


class CollectionExportResult(ApiModel):
    exported: int
    skipped: int
    target_dir: str


class ResourceBatchFailedItem(ApiModel):
    """单条失败原因。"""

    id: int
    message: str


class ResourceBatchResult(ApiModel):
    """批量结果：已成功 id 与失败清单。"""

    ok: list[int] = Field(default_factory=list)
    failed: list[ResourceBatchFailedItem] = Field(default_factory=list)


class ImportJob(ApiModel):
    """导入进度。"""

    job_id: str
    status: str
    phase: str
    total: int
    done: int
    imported: int
    skipped_duplicate: int
    skipped_error: int
    error: str | None = None
    message: str | None = None
    code: str | None = None
    details: list[str] = Field(default_factory=list)
