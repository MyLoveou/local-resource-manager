"""资源待办（立刻写入）。"""
from fastapi import APIRouter, Depends, HTTPException

from app.library.api.deps import get_repos
from app.library.application.schemas import TodoCreate, TodoPatch
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.library.domain.models import Resource

router = APIRouter(prefix="/resources", tags=["library-todos"])


@router.post("/{resource_id}/todos", response_model=Resource)
async def create_todo(
    resource_id: int,
    body: TodoCreate,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    resources, tasks = repos
    try:
        resource = await LibraryQueryService(resources, tasks).add_todo(resource_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if resource is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return resource


@router.patch("/{resource_id}/todos/{todo_id}", response_model=Resource)
async def patch_todo(
    resource_id: int,
    todo_id: int,
    body: TodoPatch,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    resources, tasks = repos
    try:
        resource = await LibraryQueryService(resources, tasks).patch_todo(resource_id, todo_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if resource is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return resource


@router.delete("/{resource_id}/todos/{todo_id}", response_model=Resource)
async def delete_todo(
    resource_id: int,
    todo_id: int,
    repos: tuple[ResourceRepository, TaskSummaryRepository] = Depends(get_repos),
) -> Resource:
    resources, tasks = repos
    resource = await LibraryQueryService(resources, tasks).delete_todo(resource_id, todo_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="todo not found")
    return resource
