"""下载任务用例。"""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.download.application.aria2 import find_aria2c, pull_magnet, remove_magnet
from app.download.application.engine import (
    DownloadAbort,
    filename_from_url,
    is_video_name,
    stream_to_file,
)
from app.download.application.errors import DownloadError
from app.download.application.ingest import ingest_downloaded_video
from app.download.application.magnet import validate_magnet
from app.download.application.ssrf import validate_http_url
from app.download.domain.models import DownloadStatus, DownloadTask
from app.download.infrastructure.repo import DownloadRepository
from app.library.application.packages.resource_package import default_library_store
from app.shared.constants import DownloadEngine, Protocol
from app.shared.errors import InvalidStateError
from app.shared.log import logger

_abort: dict[int, str] = {}
_magnet_gids: dict[int, str] = {}


def _signal(task_id: int, reason: str) -> None:
    _abort[task_id] = reason


def _clear_signal(task_id: int) -> None:
    _abort.pop(task_id, None)


def staging_root(db_path: Path) -> Path:
    return db_path.parent / "downloads"


async def create_task(session: AsyncSession, url: str, db_path: Path) -> DownloadTask:
    text = (url or "").strip()
    if text.lower().startswith("magnet:"):
        link = validate_magnet(text)
        if find_aria2c() is None:
            raise DownloadError("未找到 aria2，无法下载磁力", 400)
        repo = DownloadRepository(session)
        task = await repo.create(
            DownloadTask(
                url=link.canonical,
                protocol=Protocol.MAGNET,
                engine=DownloadEngine.ARIA2,
                status=DownloadStatus.QUEUED,
                filename=link.display_name,
            )
        )
        assert task.id is not None
        dest_dir = staging_root(db_path) / str(task.id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        task.save_path = str(dest_dir)
        return await repo.save(task)

    cleaned = validate_http_url(text)
    name = filename_from_url(cleaned)
    if name is not None and not is_video_name(name):
        raise DownloadError("本刀仅视频", 400)
    repo = DownloadRepository(session)
    task = await repo.create(
        DownloadTask(
            url=cleaned,
            protocol=Protocol.HTTP,
            engine=DownloadEngine.HTTPX,
            status=DownloadStatus.QUEUED,
            filename=name,
        )
    )
    assert task.id is not None
    dest_dir = staging_root(db_path) / str(task.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = name or "video.mp4"
    task.save_path = str(dest_dir / filename)
    return await repo.save(task)


async def list_tasks(session: AsyncSession) -> list[DownloadTask]:
    return await DownloadRepository(session).list_all()


async def get_task(session: AsyncSession, task_id: int) -> DownloadTask:
    task = await DownloadRepository(session).get(task_id)
    if task is None:
        raise DownloadError("任务不存在", 404)
    return task


async def pause_task(session: AsyncSession, task_id: int) -> DownloadTask:
    repo = DownloadRepository(session)
    task = await get_task(session, task_id)
    try:
        task.pause()
    except InvalidStateError as exc:
        raise DownloadError("当前不能暂停", 400) from exc
    saved = await repo.save(task)
    _signal(task_id, "paused")
    return saved


async def resume_task(session: AsyncSession, task_id: int) -> DownloadTask:
    repo = DownloadRepository(session)
    task = await get_task(session, task_id)
    try:
        task.requeue()
    except InvalidStateError as exc:
        raise DownloadError("当前不能恢复", 400) from exc
    _clear_signal(task_id)
    return await repo.save(task)


async def cancel_task(session: AsyncSession, task_id: int) -> DownloadTask:
    repo = DownloadRepository(session)
    task = await get_task(session, task_id)
    if task.is_terminal:
        raise DownloadError("任务已结束", 400)
    task.mark_failed("已取消")
    saved = await repo.save(task)
    _signal(task_id, "cancelled")
    gid = _magnet_gids.pop(task_id, None)
    if gid:
        await remove_magnet(gid)
    _remove_staging(saved.save_path)
    return saved


async def run_task(
    session_factory: async_sessionmaker,
    task_id: int,
    db_path: Path,
    *,
    client=None,
    aria2=None,
) -> None:
    async with session_factory() as session:
        repo = DownloadRepository(session)
        task = await repo.get(task_id)
        if task is None or task.status != DownloadStatus.QUEUED:
            return
        _clear_signal(task_id)
        task.start()
        task.speed = 0
        task.error = None
        task = await repo.save(task)

    magnet = task.protocol == Protocol.MAGNET
    if magnet:
        dest_dir = Path(task.save_path or staging_root(db_path) / str(task_id))
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir
        resume_from = 0
    else:
        dest = Path(task.save_path or staging_root(db_path) / str(task_id) / (task.filename or "video.mp4"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        resume_from = dest.stat().st_size if dest.is_file() else 0
        dest_dir = dest.parent

    async def on_progress(downloaded: int, total: int | None, speed: int) -> None:
        async with session_factory() as session:
            repo = DownloadRepository(session)
            current = await repo.get(task_id)
            if current is None or current.status != DownloadStatus.RUNNING:
                return
            current.report_progress(downloaded, total, speed)
            await repo.save(current)

    async def should_abort() -> str | None:
        reason = _abort.get(task_id)
        if reason:
            return reason
        async with session_factory() as session:
            current = await DownloadRepository(session).get(task_id)
        if current is None:
            return "cancelled"
        if current.status == DownloadStatus.PAUSED:
            return "paused"
        if current.status == DownloadStatus.FAILED:
            return "cancelled"
        return None

    def remember(gid: str) -> None:
        _magnet_gids[task_id] = gid

    try:
        if magnet:
            result, _gid = await pull_magnet(
                task.url,
                dest_dir,
                existing_gid=_magnet_gids.get(task_id),
                on_progress=on_progress,
                should_abort=should_abort,
                on_gid=remember,
                client=aria2,
            )
        else:
            result = await stream_to_file(
                task.url,
                dest,
                resume_from=resume_from,
                on_progress=on_progress,
                should_abort=should_abort,
                client=client,
            )
    except DownloadAbort as abort:
        if abort.reason == "paused":
            if abort.gid:
                _magnet_gids[task_id] = abort.gid
            async with session_factory() as session:
                repo = DownloadRepository(session)
                current = await repo.get(task_id)
                if current is not None and current.status == DownloadStatus.RUNNING:
                    current.pause()
                    await repo.save(current)
            return
        _magnet_gids.pop(task_id, None)
        return
    except Exception as exc:
        _magnet_gids.pop(task_id, None)
        message = str(exc) or "下载失败"
        logger.warning("下载失败 task=%s: %s", task_id, exc)
        async with session_factory() as session:
            repo = DownloadRepository(session)
            current = await repo.get(task_id)
            if current is not None and not current.is_terminal:
                current.mark_failed(message)
                await repo.save(current)
        return

    try:
        resource_id = await ingest_downloaded_video(
            session_factory,
            result.path,
            default_library_store(db_path),
        )
    except Exception as exc:
        logger.warning("下载入库失败 task=%s: %s", task_id, exc)
        async with session_factory() as session:
            repo = DownloadRepository(session)
            current = await repo.get(task_id)
            if current is not None and not current.is_terminal:
                current.filename = result.filename
                current.downloaded_bytes = result.downloaded
                current.total_bytes = result.total
                current.mark_failed(str(exc) or "入库失败")
                await repo.save(current)
        return

    async with session_factory() as session:
        repo = DownloadRepository(session)
        current = await repo.get(task_id)
        if current is None or current.is_terminal:
            return
        current.filename = result.filename
        current.save_path = str(result.path)
        current.downloaded_bytes = result.downloaded
        current.total_bytes = result.total
        current.speed = 0
        current.target_resource_id = resource_id
        current.mark_done()
        await repo.save(current)
    _magnet_gids.pop(task_id, None)
    if magnet:
        _remove_staging(str(dest_dir))
    else:
        _remove_staging(str(result.path))


def _remove_staging(path: str | None) -> None:
    if not path:
        return
    target = Path(path)
    try:
        if target.is_file():
            target.unlink()
            parent = target.parent
            if (
                parent.name.isdigit()
                and parent.parent.name == "downloads"
                and parent.is_dir()
                and not any(parent.iterdir())
            ):
                parent.rmdir()
            return
        if target.is_dir() and target.name.isdigit() and target.parent.name == "downloads":
            shutil.rmtree(target)
    except OSError:
        logger.warning("无法删除暂存 %s", target)
