"""分类树 API：每类型的树、管理与保存视图清理。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import (
    CategoryCreate,
    CategoryList,
    CategoryPatch,
)
from app.library.application.use_cases import CategoryService
from app.library.domain.models import ResourceType
from app.library.infrastructure.repositories import (
    CategoryRepository,
    SavedViewRepository,
)
from app.shared.db.db import get_session

router = APIRouter(prefix="/categories", tags=["library-categories"])


def _service(session: AsyncSession = Depends(get_session)) -> CategoryService:
    return CategoryService(CategoryRepository(session), SavedViewRepository(session))


@router.get("", response_model=CategoryList)
async def list_categories(
    type_: ResourceType = Query(alias="type"),
    service: CategoryService = Depends(_service),
) -> CategoryList:
    return CategoryList(items=await service.tree(type_))


@router.post("", response_model=CategoryList)
async def create_category(
    body: CategoryCreate,
    service: CategoryService = Depends(_service),
) -> CategoryList:
    await service.create(body.type, body.parent_id, body.name, body.sort)
    return CategoryList(items=await service.tree(body.type))


@router.patch("/{category_id}", response_model=CategoryList)
async def patch_category(
    category_id: int,
    body: CategoryPatch,
    service: CategoryService = Depends(_service),
) -> CategoryList:
    updated = await service.patch(
        category_id,
        name=body.name,
        parent_id=body.parent_id,
        update_parent="parent_id" in body.model_fields_set,
        sort=body.sort,
    )
    return CategoryList(items=await service.tree(updated.type))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    service: CategoryService = Depends(_service),
) -> None:
    await service.delete(category_id)
