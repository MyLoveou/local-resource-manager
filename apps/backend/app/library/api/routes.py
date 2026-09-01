"""资源库子应用 API（挂载于 /library）。"""
from fastapi import Depends, FastAPI, HTTPException, Query

from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.db import get_connection
from app.shared.models import Resource, ResourceStatus, ResourceType

app = FastAPI(
    title="library-app",
    version="0.0.0",
    description="资源库应用：概览 / 资源 / 标签 / 设置 / 适配器",
    root_path="/library",
)


def _service(conn=Depends(get_connection)) -> tuple[ResourceRepository, TaskSummaryRepository]:
    """组装仓储（每请求一个短连接）。"""
    return ResourceRepository(conn), TaskSummaryRepository(conn)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "library", "version": "0.0.0"}


@app.get("/overview")
def overview(repos=Depends(_service)) -> object:
    """首页概览：统计 + 最近添加 + 任务计数。"""
    resources, tasks = repos
    return LibraryQueryService(resources, tasks).overview()


@app.get("/resources", response_model=list[Resource])
def list_resources(
    type_: ResourceType | None = Query(default=None, alias="type"),
    status: ResourceStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repos=Depends(_service),
) -> list[Resource]:
    """资源列表（可按类型/状态过滤）。"""
    resources, _ = repos
    return resources.list(type_, status, limit, offset)


@app.get("/resources/{resource_id}", response_model=Resource)
def get_resource(resource_id: int, repos=Depends(_service)) -> Resource:
    """资源详情。"""
    resources, _ = repos
    resource = resources.get(resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@app.post("/resources", response_model=Resource)
def create_resource(resource: Resource, repos=Depends(_service)) -> Resource:
    """创建资源（入库）。"""
    resources, _ = repos
    return resources.create(resource)
