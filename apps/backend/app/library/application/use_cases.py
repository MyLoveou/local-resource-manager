"""资源库应用用例（编排仓储 → DTO）。"""
from app.library.application.schemas import (
    Overview,
    ResourcePage,
    ResourceSortField,
    ResourceStats,
    TaskSummary,
)
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.models import ResourceStatus, ResourceType


class LibraryQueryService:
    """资源库只读用例：概览、资源查询。"""

    def __init__(self, resources: ResourceRepository, tasks: TaskSummaryRepository):
        self._resources = resources
        self._tasks = tasks

    async def overview(self) -> Overview:
        """首页概览：统计 + 最近添加 + 任务计数。"""
        return Overview(
            stats=ResourceStats(**await self._resources.stats()),
            recent=await self._resources.recent(limit=12),
            tasks=TaskSummary(**await self._tasks.summary()),
        )

    async def list_page(
        self,
        type_: ResourceType | None,
        status: ResourceStatus | None,
        limit: int,
        offset: int,
        sort: ResourceSortField,
        order: str,
    ) -> ResourcePage:
        """分页列表。sort 预留；MVP 仅 createdAt。"""
        _ = sort
        total = await self._resources.count(type_, status)
        items = await self._resources.list(type_, status, limit, offset, order)
        return ResourcePage(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )
