"""资源库应用 DTO（API 契约，继承 ApiModel 以输出 camelCase）。"""
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from app.library.domain.models import SourceKind
from app.shared.models import ApiModel
from app.library.domain.models import (
    Category,
    Character,
    Person,
    Resource,
    ResourceType,
    SavedView,
    SavedViewFilters,
    StorageKind,
    Tag,
    TimelineNote,
    Work,
)
from app.shared.value_objects import Rating


class ResourceStats(ApiModel):
    """?????"""

    by_type: dict[str, int] = Field(default_factory=dict)
    previews_by_type: dict[str, list[str]] = Field(default_factory=dict)
    total_size_bytes: int = 0
    trashed_count: int = 0
    lost_count: int = 0


class TaskSummary(ApiModel):
    """进行中任务概览。"""

    running_scrape_jobs: int = 0
    failed_scrape_jobs: int = 0
    active_downloads: int = 0


class ConsumptionItem(ApiModel):
    """????/?????"""

    id: int
    resource_id: int
    title: str
    type: str
    action: str
    thumbnail_path: str | None = None
    duration: float | None = None
    format: str | None = None
    created_at: str | None = None


class Overview(ApiModel):
    """首页聚合：统计 + 最近资源 + 任务 + 工作 + 消费。"""

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
    """全库混排的合集卡。"""

    card_type: Literal["collection"] = "collection"
    id: int
    title: str
    member_count: int = 0
    updated_at: str | None = None
    preview_thumbnails: list[str] = Field(default_factory=list)


class HomeSummary(Overview):
    """资源工作台聚合。"""

    collections: list[CollectionCard] = Field(default_factory=list)
    saved_timelines: list[SavedView] = Field(default_factory=list)


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
    preview_thumbnails: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class CollectionList(ApiModel):
    items: list[CollectionOut]


class CollectionAddItem(ApiModel):
    resource_id: int


class CollectionAddItems(ApiModel):
    """批量加入合集；忽略重复成员。"""

    resource_ids: list[int] = Field(min_length=1, max_length=200)


class CollectionAddItemsResult(ApiModel):
    added: int
    skipped: int
    missing: int


class CollectionMove(ApiModel):
    direction: Literal["up", "down"]


class ResourcePatch(ApiModel):
    """资源部分更新。tag_names 若出现则替换标签；category_ids 为空数组时清空分类。"""

    title: str | None = None
    description: str | None = None
    synopsis: str | None = None
    author: str | None = None
    rating: Rating | None = None
    category_ids: list[int] | None = None
    tag_names: list[str] | None = None
    exif_taken_at: str | None = None
    timeline_visible: bool | None = None
    map_visible: bool | None = None
    character_ids: list[int] | None = None
    person_ids: list[int] | None = None


class PhotoTile(ApiModel):
    id: int
    title: str = ""
    kind: Literal["image", "video"] = "image"
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    thumbnail_path: str | None = None
    taken_at: str | None = None
    lat: float | None = None
    lng: float | None = None


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


class ThumbnailBackfillResult(ApiModel):
    scanned: int = 0
    repaired: int = 0
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


class CategoryNode(ApiModel):
    id: int
    type: ResourceType
    parent_id: int | None = None
    name: str
    sort: int = 0
    is_system: bool = False
    count: int = 0
    children: list["CategoryNode"] = Field(default_factory=list)


class CategoryList(ApiModel):
    """分类树（含计数）。"""

    items: list[CategoryNode]


class CategoryCreate(ApiModel):
    type: ResourceType
    parent_id: int | None = None
    name: str
    sort: int = 0


class CategoryPatch(ApiModel):
    name: str | None = None
    parent_id: int | None = None
    sort: int | None = None


class TimelineNoteUpsert(ApiModel):
    title: str = Field(default="", max_length=200)
    body: str | None = Field(default=None, max_length=5000)
    location_name: str | None = Field(default=None, max_length=200)


class TimelineNoteList(ApiModel):
    items: list[TimelineNote] = Field(default_factory=list)


class SavedViewCreate(ApiModel):
    kind: Literal["timeline", "map"] = "timeline"
    scope: Literal["image", "video", "media"] = "image"
    # 兼容旧客户端；新客户端只发 scope
    type: ResourceType | None = None
    name: str
    filters: SavedViewFilters = Field(default_factory=SavedViewFilters)
    sort: str = "takenAt"


class SavedViewPatch(ApiModel):
    scope: Literal["image", "video", "media"] | None = None
    name: str | None = None
    filters: SavedViewFilters | None = None
    sort: str | None = None


class SavedViewList(ApiModel):
    items: list[SavedView]


class CharacterCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    work_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    cover_resource_id: int | None = None
    aliases: list[str] = Field(default_factory=list)


class CharacterPatch(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    work_name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    cover_resource_id: int | None = None
    aliases: list[str] | None = None


class CharacterMergeRequest(ApiModel):
    source_id: int


class CharacterList(ApiModel):
    items: list[Character] = Field(default_factory=list)


class PersonCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    cover_resource_id: int | None = None
    aliases: list[str] = Field(default_factory=list)


class PersonPatch(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    cover_resource_id: int | None = None
    aliases: list[str] | None = None


class PersonMergeRequest(ApiModel):
    source_id: int


class PersonList(ApiModel):
    items: list[Person] = Field(default_factory=list)


class WorkList(ApiModel):
    items: list[Work] = Field(default_factory=list)


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
    map_visible: bool | None = None
    category_ids: list[int] | None = None
    tag_names: list[str] | None = None


class ImportJobCreated(ApiModel):
    """已接受的导入任务。"""

    job_id: str


class ResourceBatchRequest(ApiModel):
    """批量操作（移回收站/恢复/彻底删除/批量打标）；ids 去重后逐条处理，200 返回每项结果。"""

    action: Literal[
        "trash",
        "restore",
        "purge",
        "add_tags",
        "add_categories",
        "remove_categories",
        "add_characters",
        "remove_characters",
        "add_persons",
        "remove_persons",
    ]
    ids: list[int] = Field(min_length=1, max_length=200)
    tag_names: list[str] | None = None
    category_ids: list[int] | None = None
    character_ids: list[int] | None = None
    person_ids: list[int] | None = None


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
