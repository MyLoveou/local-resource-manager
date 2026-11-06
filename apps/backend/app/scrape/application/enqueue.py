"""导入成功后入队 search；只写 job 行，不跑 HTTP。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.scrape.application.jobs import create_or_reuse_job
from app.scrape.application.providers import enqueue_after_import
from app.scrape.application.queue import enqueue_job, worker_is_running
from app.scrape.domain.models import ScrapeJobStatus
from app.shared.log import logger
from app.library.domain.models import ResourceType


async def enqueue_search_after_import(
    session: AsyncSession, resource_id: int | None, type_: ResourceType, query: str | None = None
) -> None:
    if resource_id is None or not enqueue_after_import(type_):
        return
    try:
        # 有精确 query（如文件名里的 BV）时 force 新建任务直搜
        job = await create_or_reuse_job(session, resource_id, force=bool(query), query=query)
        if job.id is not None and job.status == ScrapeJobStatus.QUEUED and worker_is_running():
            await enqueue_job(job.id)
    except Exception:
        logger.exception("导入后入队刮削失败 resource=%s", resource_id)
