"""资源库应用 DTO（API 契约，继承 ApiModel 以输出 camelCase）。"""
from enum import Enum

from pydantic import Field

from app.shared.models import ApiModel, Resource
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
    """资源部分更新（仅标题/描述/评分）。"""

    title: str | None = None
    description: str | None = None
    rating: Rating | None = None
