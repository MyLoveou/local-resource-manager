"""首页概览。"""
from fastapi import APIRouter, Depends

from app.library.api.deps import get_repos
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository

router = APIRouter(tags=["library-overview"])


@router.get("/overview")
async def overview(
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> object:
    """首页概览：统计 + 最近添加 + 任务计数。"""
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).overview()
