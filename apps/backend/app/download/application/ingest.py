"""下载完成后复制进视频库。"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.library.application.import_service import ImportService, hash_file
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.library.domain.models import ResourceType


async def ingest_downloaded_video(
    session_factory: async_sessionmaker[AsyncSession],
    path: Path,
    store_root: Path,
) -> int:
    job = ImportJobState(id=f"dl-{path.name}")
    service = ImportService(session_factory=session_factory, store_root=store_root)
    await service.run(job, ResourceType.VIDEO, "file", [str(path)])
    if job.skipped_error:
        raise RuntimeError(job.error or "入库失败")
    digest, _size = hash_file(path)
    async with session_factory() as session:
        resource_id = await ResourceRepository(session).resource_id_by_sha256(digest)
    if resource_id is None:
        raise RuntimeError("入库后未找到资源")
    return resource_id
