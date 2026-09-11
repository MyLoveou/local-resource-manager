"""资源集合与单项。"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.library.api.deps import get_repos
from app.library.application.schemas import ResourcePage, ResourcePatch, ResourceSortField
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.models import Resource, ResourceStatus, ResourceType

router = APIRouter(prefix="/resources", tags=["library-resources"])


@router.get("", response_model=ResourcePage)
async def list_resources(
    type_: ResourceType | None = Query(default=None, alias="type"),
    status: ResourceStatus | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: ResourceSortField = Query(default=ResourceSortField.CREATED_AT),
    order: Literal["asc", "desc"] = Query(default="desc"),
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> ResourcePage:
    """资源分页列表（可按类型/状态过滤）。"""
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).list_page(
        type_, status, limit, offset, sort, order
    )


@router.get("/{resource_id}", response_model=Resource)
async def get_resource(
    resource_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """资源详情。"""
    resources, _ = repos
    resource = await resources.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.post("", response_model=Resource)
async def create_resource(
    resource: Resource,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """创建资源（入库）。"""
    resources, _ = repos
    return await resources.create(resource)


@router.patch("/{resource_id}", response_model=Resource)
async def patch_resource(
    resource_id: int,
    body: ResourcePatch,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """部分更新标题/描述/评分。"""
    resources, tasks = repos
    resource = await LibraryQueryService(resources, tasks).patch(resource_id, body)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.delete("/{resource_id}", response_model=Resource)
async def delete_resource(
    resource_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """软删：移入回收站。"""
    resources, tasks = repos
    resource = await LibraryQueryService(resources, tasks).trash(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource
