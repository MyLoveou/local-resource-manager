"""任务中心 API：读状态、取消、重试。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared import tasks
from app.shared.db.db import get_session
from app.shared.models import ApiModel

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskOut(ApiModel):
    id: str
    kind: str
    resource_id: int | None = None
    title: str
    state: str
    done: int = 0
    total: int = 0
    percent: float = 0
    attempts: int = 0
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class TaskListOut(ApiModel):
    items: list[TaskOut] = Field(default_factory=list)


def _to_out(row: dict) -> TaskOut:
    return TaskOut(
        id=row["id"],
        kind=row["kind"],
        resource_id=row["resource_id"],
        title=row["title"],
        state=row["state"],
        done=row["done"] or 0,
        total=row["total"] or 0,
        percent=row["percent"] or 0,
        attempts=row["attempts"] or 0,
        error=row["error"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )


@router.get("", response_model=TaskListOut)
async def list_tasks(
    state: str | None = None,
    active: bool = False,
    session: AsyncSession = Depends(get_session),
) -> TaskListOut:
    """state=all 看全部；active=1 只看排队与运行中。"""
    states: tuple[str, ...] | None
    if active:
        states = tasks.ACTIVE_STATES
    elif state and state != "all":
        states = (state,)
    else:
        states = None
    rows = await tasks.list_tasks(session, states=states)
    return TaskListOut(items=[_to_out(row) for row in rows])


@router.post("/{task_id}/cancel", response_model=TaskOut)
async def cancel_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
) -> TaskOut:
    row = (
        await session.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id})
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row["state"] not in tasks.ACTIVE_STATES:
        raise HTTPException(status_code=409, detail="任务已结束")
    await tasks.cancel(session, task_id)
    row = (
        await session.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id})
    ).mappings().first()
    return _to_out(dict(row))


@router.post("/{task_id}/retry", response_model=TaskOut)
async def retry_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
) -> TaskOut:
    """重试：把失败/中断的任务放回队列。

    导入需要「继续」按钮（会跳过已复制文件），不在这个通用重试里，
    避免用户以为点了就会接着原来的进度。
    """
    row = (
        await session.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id})
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if row["kind"] == tasks.KIND_IMPORT:
        raise HTTPException(status_code=400, detail="导入请使用「继续导入」")
    if row["state"] not in (tasks.FAILED, tasks.INTERRUPTED, tasks.CANCELLED):
        raise HTTPException(status_code=409, detail="只有失败/中断的任务可以重试")
    await session.execute(
        text(
            "UPDATE tasks SET state = :queued, error = NULL, finished_at = NULL"
            " WHERE id = :id"
        ),
        {"queued": tasks.QUEUED, "id": task_id},
    )
    await session.commit()
    row = (
        await session.execute(text("SELECT * FROM tasks WHERE id = :id"), {"id": task_id})
    ).mappings().first()
    return _to_out(dict(row))
