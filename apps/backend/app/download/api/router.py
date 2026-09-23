"""下载模块路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.download.application.errors import DownloadError
from app.download.application.queue import enqueue_download
from app.download.application.schemas import DownloadTaskCreate
from app.download.application.service import (
    cancel_task,
    create_task,
    get_task,
    list_tasks,
    pause_task,
    resume_task,
)
from app.shared.config import settings
from app.shared.db.db import get_session

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "download", "version": "0.1.0"}


def _err(exc: DownloadError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/tasks", status_code=201)
async def post_task(body: DownloadTaskCreate, session: AsyncSession = Depends(get_session)):
    try:
        task = await create_task(session, body.url, settings.db_path)
    except DownloadError as exc:
        raise _err(exc) from exc
    assert task.id is not None
    await enqueue_download(task.id)
    return task


@router.get("/tasks")
async def get_tasks(session: AsyncSession = Depends(get_session)):
    return await list_tasks(session)


@router.get("/tasks/{task_id}")
async def get_one(task_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await get_task(session, task_id)
    except DownloadError as exc:
        raise _err(exc) from exc


@router.post("/tasks/{task_id}/pause")
async def post_pause(task_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await pause_task(session, task_id)
    except DownloadError as exc:
        raise _err(exc) from exc


@router.post("/tasks/{task_id}/resume")
async def post_resume(task_id: int, session: AsyncSession = Depends(get_session)):
    try:
        task = await resume_task(session, task_id)
    except DownloadError as exc:
        raise _err(exc) from exc
    assert task.id is not None
    await enqueue_download(task.id)
    return task


@router.post("/tasks/{task_id}/cancel")
async def post_cancel(task_id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await cancel_task(session, task_id)
    except DownloadError as exc:
        raise _err(exc) from exc
