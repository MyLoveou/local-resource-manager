"""保存的时间线筛选器 API。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import (
    SavedViewCreate,
    SavedViewList,
    SavedViewPatch,
)
from app.library.application.use_cases import SavedViewService
from app.library.domain.models import ResourceType, SavedView
from app.library.infrastructure.repositories import CategoryRepository, SavedViewRepository
from app.shared.db.db import get_session

router = APIRouter(prefix="/saved-views", tags=["library-saved-views"])


def _service(session: AsyncSession = Depends(get_session)) -> SavedViewService:
    return SavedViewService(SavedViewRepository(session), CategoryRepository(session))


@router.get("", response_model=SavedViewList)
async def list_saved_views(
    scope: str | None = Query(default=None),
    type_: ResourceType | None = Query(default=None, alias="type"),
    service: SavedViewService = Depends(_service),
) -> SavedViewList:
    return SavedViewList(items=await service.list(scope or (type_.value if type_ else None)))


@router.get("/{view_id}", response_model=SavedView)
async def get_saved_view(
    view_id: int,
    service: SavedViewService = Depends(_service),
) -> SavedView:
    return await service.get(view_id)


@router.post("", response_model=SavedView)
async def create_saved_view(
    body: SavedViewCreate,
    service: SavedViewService = Depends(_service),
) -> SavedView:
    return await service.create(body)


@router.patch("/{view_id}", response_model=SavedView)
async def patch_saved_view(
    view_id: int,
    body: SavedViewPatch,
    service: SavedViewService = Depends(_service),
) -> SavedView:
    return await service.patch(view_id, body)


@router.delete("/{view_id}", status_code=204)
async def delete_saved_view(
    view_id: int,
    service: SavedViewService = Depends(_service),
) -> None:
    await service.delete(view_id)
