"""分类词表只读列表。"""
from fastapi import APIRouter, Depends

from app.library.api.deps import get_repos
from app.library.application.schemas import CategoryList
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository

router = APIRouter(prefix="/categories", tags=["library-categories"])


@router.get("", response_model=CategoryList)
async def list_categories(
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> CategoryList:
    resources, _ = repos
    return CategoryList(items=await resources.list_categories())
