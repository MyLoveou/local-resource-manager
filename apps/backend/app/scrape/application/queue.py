"""进程内刮削队列。"""

from __future__ import annotations

import asyncio

from app.scrape.application.jobs import run_search
from app.shared.db.db import get_session_factory
from app.shared.log import logger

_queue: asyncio.Queue[int] | None = None
_worker: asyncio.Task[None] | None = None


def scrape_queue() -> asyncio.Queue[int]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def enqueue_job(job_id: int) -> None:
    await scrape_queue().put(job_id)


async def _worker_loop() -> None:
    queue = scrape_queue()
    while True:
        job_id = await queue.get()
        try:
            factory = get_session_factory()
            async with factory() as session:
                await run_search(session, job_id)
                await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("刮削任务失败 job=%s", job_id)
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
