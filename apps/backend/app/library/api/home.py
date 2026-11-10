"""资源工作台首页聚合。"""
from fastapi import APIRouter, Depends

from app.library.api.deps import get_repos
from app.library.application.schemas import HomeSummary
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository

router = APIRouter(tags=["library-home"])


@router.get("/home", response_model=HomeSummary)
async def home(
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> HomeSummary:
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).home()
