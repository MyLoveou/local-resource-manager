"""资源库应用用例（编排仓储 → DTO）。"""
from app.library.application.schemas import Overview, ResourceStats, TaskSummary
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository


class LibraryQueryService:
    """资源库只读用例：概览、资源查询。"""

    def __init__(self, resources: ResourceRepository, tasks: TaskSummaryRepository):
        self._resources = resources
        self._tasks = tasks

    def overview(self) -> Overview:
        """首页概览：统计 + 最近添加 + 任务计数。"""
        return Overview(
            stats=ResourceStats(**self._resources.stats()),
            recent=self._resources.recent(limit=12),
            tasks=TaskSummary(**self._tasks.summary()),
        )
