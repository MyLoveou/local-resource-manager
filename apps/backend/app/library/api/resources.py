"""资源集合与单项。"""
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.library.api.deps import get_repos
from app.library.application.packages.resource_package import default_library_store
from app.library.application.schemas import (
    CoverReplace,
    ResourceBatchRequest,
    ResourceBatchResult,
    ResourcePage,
    ResourcePatch,
    ResourceSortField,
    SubtitleAdd,
)
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.config import settings
from app.shared.errors import InvalidStateError
from app.shared.models import Resource, ResourceStatus, ResourceType

router = APIRouter(prefix="/resources", tags=["library-resources"])


def _library_file_or_404(raw_path: str) -> Path:
    """只允许打开库目录内的文件。"""
    store = default_library_store(settings.db_path).resolve()
    try:
        resolved = Path(raw_path).resolve()
    except OSError as exc:
        raise HTTPException(status_code=404, detail="file not found") from exc
    if not resolved.is_file() or not resolved.is_relative_to(store):
        raise HTTPException(status_code=404, detail="file not found")
    return resolved


def _file_response(path: Path, *, long_cache: bool) -> FileResponse:
    """缩略图长缓存；原片短缓存。"""
    suffix = path.suffix.lower()
    media_type = {
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
    }.get(suffix)
    response = FileResponse(path, media_type=media_type)
    if long_cache:
        response.headers["Cache-Control"] = "private, max-age=86400"
    else:
        response.headers["Cache-Control"] = "private, max-age=120"
    return response


@router.get("", response_model=ResourcePage)
async def list_resources(
    type_: ResourceType | None = Query(default=None, alias="type"),
    status: ResourceStatus | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    after_created_at: str | None = Query(default=None, alias="afterCreatedAt"),
    after_id: int | None = Query(default=None, alias="afterId"),
    sort: ResourceSortField = Query(default=ResourceSortField.CREATED_AT),
    order: Literal["asc", "desc"] = Query(default="desc"),
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> ResourcePage:
    """资源分页列表（可按类型/状态过滤）。"""
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).list_page(
        type_, status, limit, offset, sort, order,
        after_created_at=after_created_at,
        after_id=after_id,
    )


@router.post("/batch", response_model=ResourceBatchResult)
async def batch_resources(
    body: ResourceBatchRequest,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> ResourceBatchResult:
    """批量 trash / restore / purge；部分失败仍返回 200。"""
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).batch(body.action, body.ids)


@router.get("/{resource_id}/content")
async def get_resource_content(
    resource_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> FileResponse:
    """流式返回库内 primary 副本。"""
    resources, _ = repos
    row = await resources.get_file_by_role(resource_id, "primary")
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    return _file_response(_library_file_or_404(row.path), long_cache=False)


@router.get("/{resource_id}/files/{file_id}/content")
async def get_resource_file_content(
    resource_id: int,
    file_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> FileResponse:
    """流式返回包内指定文件。"""
    resources, _ = repos
    row = await resources.get_file(resource_id, file_id)
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    long_cache = row.role == "thumbnail"
    return _file_response(_library_file_or_404(row.path), long_cache=long_cache)


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


@router.post("/{resource_id}/cover", response_model=Resource)
async def replace_cover(
    resource_id: int,
    body: CoverReplace,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """将本机图片复制为包内 cover，不替换 primary。"""
    resources, tasks = repos
    try:
        resource = await LibraryQueryService(resources, tasks).replace_cover(resource_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.post("/{resource_id}/subtitles", response_model=Resource)
async def add_subtitle(
    resource_id: int,
    body: SubtitleAdd,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """将本机字幕复制进包内，按原始视频名改名。"""
    resources, tasks = repos
    try:
        resource = await LibraryQueryService(resources, tasks).add_subtitle(resource_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    """部分更新标题/描述/评分/分类名/标签名。"""
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


@router.post("/{resource_id}/restore", response_model=Resource)
async def restore_resource(
    resource_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    """从回收站恢复。"""
    resources, tasks = repos
    try:
        resource = await LibraryQueryService(resources, tasks).restore(resource_id)
    except InvalidStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.post("/{resource_id}/purge")
async def purge_resource(
    resource_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> dict[str, bool]:
    """彻底删除：删库内包并 DROP 行。"""
    resources, tasks = repos
    try:
        ok = await LibraryQueryService(resources, tasks).purge(resource_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="failed to delete package") from exc
    if not ok:
        raise HTTPException(status_code=404, detail="resource not found")
    return {"ok": True}
