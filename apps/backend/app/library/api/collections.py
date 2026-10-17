"""合集 API：/library/collections。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import (
    CollectionAddItem,
    CollectionCreate,
    CollectionExportRequest,
    CollectionExportResult,
    CollectionList,
    CollectionMove,
    CollectionOut,
    CollectionPatch,
)
from app.library.application.use_cases import CollectionService
from app.library.domain.models import Collection
from app.library.infrastructure.repositories import CollectionRepository, ResourceRepository
from app.shared.db.db import get_session

router = APIRouter(prefix="/collections", tags=["library-collections"])


def _service(
    session: AsyncSession = Depends(get_session),
) -> CollectionService:
    return CollectionService(CollectionRepository(session), ResourceRepository(session))


def _out(collection: Collection) -> CollectionOut:
    """领域模型 → API DTO（Pydantic 不跨模型类强转，需显式构造）。"""
    return CollectionOut(**collection.model_dump())


@router.get("", response_model=CollectionList)
async def list_collections(service: CollectionService = Depends(_service)) -> CollectionList:
    return CollectionList(items=[_out(item) for item in await service.list()])


@router.post("", response_model=CollectionOut)
async def create_collection(
    body: CollectionCreate,
    service: CollectionService = Depends(_service),
) -> CollectionOut:
    return _out(await service.create(body.title, body.description))


@router.get("/{collection_id}", response_model=CollectionOut)
async def get_collection(
    collection_id: int,
    service: CollectionService = Depends(_service),
) -> CollectionOut:
    return _out(await service.get(collection_id))


@router.patch("/{collection_id}", response_model=CollectionOut)
async def patch_collection(
    collection_id: int,
    body: CollectionPatch,
    service: CollectionService = Depends(_service),
) -> CollectionOut:
    return _out(await service.patch(collection_id, body.title, body.description))


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: int,
    service: CollectionService = Depends(_service),
) -> None:
    await service.delete(collection_id)


@router.get("/{collection_id}/items", response_model=list)
async def collection_members(
    collection_id: int,
    service: CollectionService = Depends(_service),
) -> list:
    return await service.members(collection_id)


@router.post("/{collection_id}/items", status_code=204)
async def add_collection_item(
    collection_id: int,
    body: CollectionAddItem,
    service: CollectionService = Depends(_service),
) -> None:
    await service.add_item(collection_id, body.resource_id)


@router.delete("/{collection_id}/items/{resource_id}", status_code=204)
async def remove_collection_item(
    collection_id: int,
    resource_id: int,
    service: CollectionService = Depends(_service),
) -> None:
    await service.remove_item(collection_id, resource_id)


@router.post("/{collection_id}/items/{resource_id}/move", status_code=204)
async def move_collection_item(
    collection_id: int,
    resource_id: int,
    body: CollectionMove,
    service: CollectionService = Depends(_service),
) -> None:
    await service.move_item(collection_id, resource_id, body.direction)


@router.post("/{collection_id}/export", response_model=CollectionExportResult)
async def export_collection(
    collection_id: int,
    body: CollectionExportRequest,
    service: CollectionService = Depends(_service),
) -> CollectionExportResult:
    """把合集成员主文件按顺序复制到目标目录（返图用）。"""
    return await service.export(collection_id, body.target_dir)


resource_collections_router = APIRouter(prefix="/resources", tags=["library-collections"])


@resource_collections_router.get("/{resource_id}/collections", response_model=CollectionList)
async def collections_of_resource(
    resource_id: int,
    service: CollectionService = Depends(_service),
) -> CollectionList:
    """某资源所属的合集（信息栏「加入合集」用）。"""
    return CollectionList(items=[_out(item) for item in await service.collections_of(resource_id)])
