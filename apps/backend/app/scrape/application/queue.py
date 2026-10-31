"""进程内刮削队列。"""

from __future__ import annotations

import asyncio

from app.scrape.application.jobs import run_search
from app.scrape.infrastructure.repo import ScrapeRepository
from app.scrape.domain.models import ScrapeJobStatus
from app.shared.db.db import get_session_factory
from app.shared import tasks
from app.shared.log import logger

import os

# 0 = 不超时（默认）。需要时设 SCRAPE_JOB_TIMEOUT=90 恢复
JOB_TIMEOUT_SEC = int(os.getenv("SCRAPE_JOB_TIMEOUT", "0"))
_queue: asyncio.Queue[int] | None = None
_worker: asyncio.Task[None] | None = None


def scrape_queue() -> asyncio.Queue[int]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def enqueue_job(job_id: int) -> None:
    await scrape_queue().put(job_id)


async def _mark_failed(job_id: int, reason: str) -> None:
    """把任务落成 failed，避免卡在 running 挡住后续任务。"""
    try:
        factory = get_session_factory()
        async with factory() as session:
            repo = ScrapeRepository(session)
            job = await repo.get_job(job_id)
            if job is not None and job.status != ScrapeJobStatus.DONE:
                job.fail(reason)
                await repo.save_job(job)
    except Exception:  # noqa: BLE001 - 兜底失败不应该再抛
        logger.exception("标记刮削失败时出错 job=%s", job_id)
async def _open_task(job_id: int) -> str | None:
    """为刮削任务建一行 tasks，标题取查询词。"""
    try:
        factory = get_session_factory()
        async with factory() as session:
            repo = ScrapeRepository(session)
            job = await repo.get_job(job_id)
            title = f"刮削 · {job.query}" if job and job.query else "刮削"
            task_id = await tasks.create(
                session,
                kind=tasks.KIND_SCRAPE,
                title=title,
                resource_id=job.resource_id if job else None,
                dedupe_key=f"scrape:{job.resource_id}:{job.query}" if job else None,
            )
            if task_id is not None:
                await tasks.start(session, task_id)
            return task_id
    except Exception:  # noqa: BLE001 - 记账失败不该影响刮削
        logger.exception("创建刮削任务记录失败 job=%s", job_id)
        return None


async def _close_task(job_id: int, reason: str) -> None:
    """失败时把对应的 tasks 行标失败。"""
    try:
        factory = get_session_factory()
        async with factory() as session:
            repo = ScrapeRepository(session)
            job = await repo.get_job(job_id)
            if job is None:
                return
            rows = await tasks.list_tasks(session, states=(tasks.RUNNING,))
            for row in rows:
                if row["kind"] == tasks.KIND_SCRAPE and row["resource_id"] == job.resource_id:
                    await tasks.fail(session, row["id"], reason)
    except Exception:  # noqa: BLE001
        logger.exception("关闭刮削任务记录失败 job=%s", job_id)
async def _worker_loop() -> None:
    queue = scrape_queue()
    while True:
        job_id = await queue.get()
        try:
            factory = get_session_factory()
            task_id = await _open_task(job_id)
            async with factory() as session:
                if JOB_TIMEOUT_SEC > 0:
                    await asyncio.wait_for(run_search(session, job_id), timeout=JOB_TIMEOUT_SEC)
                else:
                    await run_search(session, job_id)
                if task_id is not None:
                    await tasks.finish(session, task_id)
                await asyncio.sleep(0.25)
        except asyncio.TimeoutError:
            logger.warning("刮削任务超时，已标记失败 job=%s", job_id)
            await _mark_failed(job_id, "搜索超时")
            await _close_task(job_id, "搜索超时")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("刮削任务失败 job=%s", job_id)
            await _mark_failed(job_id, str(exc)[:200])
            await _close_task(job_id, str(exc)[:200])
        finally:
            queue.task_done()


def worker_is_running() -> bool:
    return _worker is not None and not _worker.done()


def start_scrape_worker() -> None:
    global _worker
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_worker_loop())


async def stop_scrape_worker() -> None:
    global _worker
    task = _worker
    _worker = None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def recover_unfinished() -> None:
    from app.scrape.infrastructure.repo import ScrapeRepository

    factory = get_session_factory()
    async with factory() as session:
        repo = ScrapeRepository(session)
        ids = await repo.list_unfinished_ids()
    for job_id in ids:
        await enqueue_job(job_id)
