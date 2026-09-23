"""进程内下载队列。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.download.application.service import run_task
from app.download.infrastructure.repo import DownloadRepository
from app.shared.config import settings
from app.shared.db.db import get_session_factory
from app.shared.log import logger

_queue: asyncio.Queue[int] | None = None
_worker: asyncio.Task[None] | None = None


def download_queue() -> asyncio.Queue[int]:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def enqueue_download(task_id: int) -> None:
    await download_queue().put(task_id)


async def _worker_loop() -> None:
    queue = download_queue()
    while True:
        task_id = await queue.get()
        try:
            factory = get_session_factory()
            await run_task(factory, task_id, Path(settings.db_path))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("下载任务失败 task=%s", task_id)
        finally:
            queue.task_done()


def start_download_worker() -> None:
    global _worker
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_worker_loop())


async def stop_download_worker() -> None:
    global _worker
    task = _worker
    _worker = None
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    from app.download.application.aria2 import shutdown_aria2

    await shutdown_aria2()


async def recover_downloads() -> None:
    factory = get_session_factory()
    async with factory() as session:
        repo = DownloadRepository(session)
        await repo.reset_running_to_queued()
        ids = await repo.list_queued_ids()
    for task_id in ids:
        await enqueue_download(task_id)
