"""资源库子应用 API（挂载于 /library）。"""
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import ResourcePage, ResourceSortField
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.library.infrastructure.seed import seed_demo_if_empty
from app.shared.db.db import get_session
from app.shared.models import Resource, ResourceStatus, ResourceType

app = FastAPI(
    title="library-app",
    version="0.0.0",
    description="资源库应用：概览 / 资源 / 标签 / 设置 / 适配器",
    root_path="/library",
)


def _service(
    session: AsyncSession = Depends(get_session),
) -> tuple[ResourceRepository, TaskSummaryRepository]:
    """组装仓储（每请求一个 AsyncSession）。"""
    return ResourceRepository(session), TaskSummaryRepository(session)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "library", "version": "0.0.0"}


@app.get("/overview")
async def overview(repos=Depends(_service)) -> object:
    """首页概览：统计 + 最近添加 + 任务计数。"""
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).overview()


@app.get("/resources", response_model=ResourcePage)
async def list_resources(
    type_: ResourceType | None = Query(default=None, alias="type"),
    status: ResourceStatus | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: ResourceSortField = Query(default=ResourceSortField.CREATED_AT),
    order: Literal["asc", "desc"] = Query(default="desc"),
    repos=Depends(_service),
) -> ResourcePage:
    """资源分页列表（可按类型/状态过滤）。"""
    resources, tasks = repos
    return await LibraryQueryService(resources, tasks).list_page(
        type_, status, limit, offset, sort, order
    )


@app.get("/resources/{resource_id}", response_model=Resource)
async def get_resource(resource_id: int, repos=Depends(_service)) -> Resource:
    """资源详情。"""
    resources, _ = repos
    resource = await resources.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@app.post("/resources", response_model=Resource)
async def create_resource(resource: Resource, repos=Depends(_service)) -> Resource:
    """创建资源（入库）。"""
    resources, _ = repos
    return await resources.create(resource)


@app.post("/dev/seed")
async def seed_demo(repos=Depends(_service)) -> dict:
    """空库时写入演示资源；已有数据则跳过。"""
    resources, _ = repos
    inserted = await seed_demo_if_empty(resources)
    return {"inserted": inserted}
