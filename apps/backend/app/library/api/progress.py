"""播放进度（video-management S1）。

- `/library/resources/{id}/progress`：上报 / 读取 / 清除单个文件的进度
- `/library/progress/resume`：继续观看列表
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.progress import ProgressService
from app.library.application.schemas import (
    PlaybackProgressIn,
    PlaybackProgressOut,
    ResumePage,
)
from app.library.infrastructure.repositories_progress import PlaybackProgressRepository
from app.shared.db.db import get_session

router = APIRouter(prefix="/progress", tags=["library-progress"])
resource_router = APIRouter(prefix="/resources", tags=["library-resources"])


def _service(session: AsyncSession) -> ProgressService:
    return ProgressService(PlaybackProgressRepository(session))


@resource_router.put("/{resource_id}/progress", response_model=PlaybackProgressOut)
async def put_progress(
    resource_id: int,
    body: PlaybackProgressIn,
    session: AsyncSession = Depends(get_session),
) -> PlaybackProgressOut:
    result = await _service(session).record(
        resource_id, body.file_id, body.position, body.duration
    )
    if result is None:
        raise HTTPException(status_code=404, detail="resource or file not found")
    return result


@resource_router.get(
    "/{resource_id}/progress", response_model=PlaybackProgressOut | None
)
async def get_progress(
    resource_id: int,
    file_id: int = Query(alias="fileId"),
    session: AsyncSession = Depends(get_session),
) -> PlaybackProgressOut | None:
    return await _service(session).get(resource_id, file_id)


@resource_router.delete("/{resource_id}/progress", status_code=204)
async def delete_progress(
    resource_id: int,
    file_id: int | None = Query(default=None, alias="fileId"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await _service(session).clear(resource_id, file_id)
    return Response(status_code=204)


@router.get("/resume", response_model=ResumePage)
async def resume(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> ResumePage:
    return await _service(session).resume(limit)
