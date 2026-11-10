"""标签词表只读列表（可按类型过滤：本类标签筛选）。"""
from fastapi import APIRouter, Depends, Query

from app.library.api.deps import get_repos
from app.library.application.schemas import TagList
from app.library.domain.models import ResourceType
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository

router = APIRouter(prefix="/tags", tags=["library-tags"])


@router.get("", response_model=TagList)
async def list_tags(
    type_: ResourceType | None = Query(default=None, alias="type"),
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> TagList:
    resources, _ = repos
    return TagList(items=await resources.list_tags(type_))
