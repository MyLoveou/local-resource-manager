"""资源库应用 DTO（API 契约，继承 ApiModel 以输出 camelCase）。"""
from enum import Enum

from pydantic import Field

from app.shared.constants import SourceKind
from app.shared.models import ApiModel, Category, Resource, ResourceType, Tag
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


class Overview(ApiModel):
    """首页概览（统计 + 最近添加 + 任务）。"""

    stats: ResourceStats
    recent: list[Resource]
    tasks: TaskSummary


class ResourceSortField(str, Enum):
    """列表排序字段（JSON camelCase）。"""

    CREATED_AT = "createdAt"


class ResourcePage(ApiModel):
    """资源列表分页信封。"""

    items: list[Resource]
    total: int
    limit: int
    offset: int
    has_more: bool


class ResourcePatch(ApiModel):
    """资源部分更新。tag_names 若出现则整表替换该资源标签；category_name 按名查找或创建分类。"""

    title: str | None = None
    description: str | None = None
    author: str | None = None
    rating: Rating | None = None
    category_name: str | None = None
    tag_names: list[str] | None = None


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


class ImportJobCreated(ApiModel):
    """已接受的导入任务。"""

    job_id: str


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
