"""download_tasks 读写。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.download.domain.models import DownloadStatus, DownloadTask
from app.shared.constants import DownloadEngine, Protocol
from app.shared.db.orm import DownloadTaskRow


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _task(row: DownloadTaskRow) -> DownloadTask:
    return DownloadTask(
        id=row.id,
        url=row.url,
        protocol=Protocol(row.protocol),
        engine=DownloadEngine(row.engine),
        status=DownloadStatus(row.status),
        save_path=row.save_path,
        downloaded_bytes=row.downloaded_bytes,
        total_bytes=row.total_bytes,
        speed=row.speed,
        error=row.error,
        target_resource_id=row.target_resource_id,
        filename=row.filename,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class DownloadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task: DownloadTask) -> DownloadTask:
        now = _now()
        row = DownloadTaskRow(
            url=task.url,
            protocol=task.protocol.value,
            engine=task.engine.value,
            status=task.status.value,
            save_path=task.save_path,
            downloaded_bytes=task.downloaded_bytes,
            total_bytes=task.total_bytes,
            speed=task.speed,
            error=task.error,
            target_resource_id=task.target_resource_id,
            filename=task.filename,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _task(row)

    async def get(self, task_id: int) -> DownloadTask | None:
        row = await self._session.get(DownloadTaskRow, task_id)
        return None if row is None else _task(row)

    async def list_all(self) -> list[DownloadTask]:
        stmt = select(DownloadTaskRow).order_by(DownloadTaskRow.id.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_task(row) for row in rows]

    async def save(self, task: DownloadTask) -> DownloadTask:
        assert task.id is not None
        row = await self._session.get(DownloadTaskRow, task.id)
        if row is None:
            raise RuntimeError("下载任务不存在")
        row.url = task.url
        row.protocol = task.protocol.value
        row.engine = task.engine.value
        row.status = task.status.value
        row.save_path = task.save_path
        row.downloaded_bytes = task.downloaded_bytes
        row.total_bytes = task.total_bytes
        row.speed = task.speed
        row.error = task.error
        row.target_resource_id = task.target_resource_id
        row.filename = task.filename
        row.updated_at = _now()
        await self._session.commit()
        await self._session.refresh(row)
        return _task(row)

    async def reset_running_to_queued(self) -> None:
        stmt = (
            update(DownloadTaskRow)
            .where(DownloadTaskRow.status == DownloadStatus.RUNNING.value)
            .values(status=DownloadStatus.QUEUED.value, updated_at=_now())
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def list_queued_ids(self) -> list[int]:
        stmt = (
            select(DownloadTaskRow.id)
            .where(DownloadTaskRow.status == DownloadStatus.QUEUED.value)
            .order_by(DownloadTaskRow.id.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [int(item) for item in rows]
