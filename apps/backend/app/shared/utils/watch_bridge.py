"""监视事件 → 导入用例的线程/异步桥。

- worker 线程回调只投递事件（call_soon_threadsafe），不碰 DB
- 处理层按资源类型**显式映射**（HANDLERS）：新增类型/差异化处理只加映射项
- file 型攒批（同类型事件合并一次导入管道，内部并发）；sha256 复用事件预计算值
- 监视导入默认不入刮削队列（auto_scrape=False）
- 剧集型（anime/av）自动导入未接入：需要目录级上下文，占位 handler
"""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Awaitable, Callable

from app.library.application.import_service import ImportService, hash_file
from app.library.application.importers import importer_for
from app.library.application.packages.layouts import layout_for
from app.library.application.packages.resource_package import ResourcePackage, default_library_store
from app.library.application.series_plan import classify_single_video
from app.library.domain.media_types import FILE_ROLE_EPISODE, FILE_ROLE_EXTRA
from app.library.domain.models import Resource, ResourceType, SourceKind
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.db.db import get_session_factory
from app.shared.fs.file_ops import FileOps
from app.shared.log import logger
from app.shared.utils.file_watcher import EventType, FileEvent, File_Extension_Map
from app.shared.utils.watch_events import watch_events

# 攒批窗口：窗口内同类型事件合并为一次导入
BATCH_WINDOW_SECONDS = 0.3


def _walk_files(root: Path, exts: frozenset[str]) -> list[str]:
    """枚举目录下匹配扩展名的文件（补扫用）。"""
    result: list[str] = []
    for p in root.rglob("*"):
        try:
            if p.is_file() and p.suffix.lower() in exts:
                result.append(str(p))
        except OSError:
            continue
    return result

# 处理层映射：资源类型 → 批量处理器（与派发层的回调 map 同构）
WatchHandler = Callable[[list[FileEvent], ResourceType], Awaitable[None]]


async def _import_files(events: list[FileEvent], type_: ResourceType) -> None:
    """file 型批量处理：多文件一次导入管道（内部并发），哈希用事件预计算值。"""
    factory = get_session_factory()
    job = ImportJobState(id=f"watch-{uuid.uuid4().hex}")
    prehashed = {e.path: e.sha256 for e in events if e.sha256}
    await ImportService(session_factory=factory).run(
        job, type_, "file", [e.path for e in events],
        prehashed=prehashed or None, auto_scrape=False,
    )
    if job.imported > 0:
        logger.info("监视批量导入完成: %s 个 → %s", job.imported, type_.value)
        watch_events.record(type_.value)
    if job.skipped_duplicate:
        logger.info("监视导入跳过（重复）: %s 个", job.skipped_duplicate)
    if job.skipped_error:
        logger.warning("监视导入跳过（错误）: %s 个", job.skipped_error)


async def _import_series(events: list[FileEvent], type_: ResourceType) -> None:
    """剧集型（anime/av）：目录级增量入库。

    事件按父目录分组；目录已有资源（extra.importSourcePath）→ 增量挂集；
    没有 → 整目录系列导入（复用 ImportService series 路径，内部已做 sha256 去重与集树解析）。
    """
    factory = get_session_factory()
    importer = importer_for(type_)
    layout = layout_for(type_)
    if importer is None or layout is None:
        logger.warning("%s 无导入策略，跳过监视事件", type_.value)
        return
    by_dir: dict[str, list[FileEvent]] = {}
    for event in events:
        parent = str(Path(event.path).resolve().parent)
        by_dir.setdefault(parent, []).append(event)
    for dir_path, dir_events in by_dir.items():
        try:
            async with factory() as session:
                repo = ResourceRepository(session)
                existing = await repo.find_by_import_source(dir_path)
                if existing is None:
                    await _bootstrap_series(factory, type_, dir_path)
                else:
                    await _append_events(repo, existing, type_, layout, dir_path, dir_events)
        except Exception as exc:  # noqa: BLE001 — 单目录失败不拖垮消费循环
            logger.warning("监视剧集导入失败 %s: %s", dir_path, exc)


async def _bootstrap_series(factory, type_: ResourceType, dir_path: str) -> None:
    """首次监视到该目录：整目录系列导入。"""
    job = ImportJobState(id=f"watch-{uuid.uuid4().hex}")
    await ImportService(session_factory=factory).run(
        job, type_, SourceKind.DIRECTORY.value, [dir_path], auto_scrape=False
    )
    if job.imported > 0:
        logger.info("监视剧集导入完成（新建）: %s → %s", dir_path, type_.value)
        watch_events.record(type_.value)
    elif job.skipped_duplicate or job.skipped_error:
        logger.info(
            "监视剧集跳过: %s（重复 %s / 错误 %s）",
            dir_path, job.skipped_duplicate, job.skipped_error,
        )


async def _append_events(
    repo: ResourceRepository,
    resource: Resource,
    type_: ResourceType,
    layout,
    dir_path: str,
    events: list[FileEvent],
) -> None:
    """增量：把监视到的新文件挂到既有系列（含季/集树）。"""
    root = Path(dir_path)
    store_root = default_library_store(settings.db_path)
    imported = 0
    skipped_dup = 0
    for event in events:
        src = Path(event.path)
        digest = event.sha256
        try:
            if digest is None:
                digest, size = await asyncio.to_thread(hash_file, src)
            else:
                size = await asyncio.to_thread(os.path.getsize, src)
        except OSError as exc:
            logger.warning("监视剧集跳过 %s: %s", src, exc)
            continue
        if await repo.file_exists_by_sha256(digest):
            skipped_dup += 1
            continue
        kind, season, episode, title = classify_single_video(root, src)
        season_row = None
        if kind == "episode":
            season_row = await repo.get_season(resource.id, season)
            if season_row is not None and await repo.get_episode(season_row.id, episode) is not None:
                skipped_dup += 1
                logger.info("监视剧集跳过（集号已存在）: %s", src.name)
                continue
        suffix = src.suffix.lower()
        if kind == "episode":
            dest_rel = f"seasons/{season:02d}/S{season:02d}E{episode:02d}{suffix}"
        else:
            dest_rel = f"extras/{src.name}"
        package = ResourcePackage(
            store_root, type_, resource.id, FileOps(),
            cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
        )
        try:
            dest = await asyncio.to_thread(package.put_relative, src, dest_rel)
        except OSError as exc:
            logger.warning("监视剧集复制失败 %s: %s", src, exc)
            continue
        file_row = await repo.add_file(
            resource.id,
            path=str(dest),
            sha256=digest,
            size=size,
            format_=suffix.lstrip("."),
            role=FILE_ROLE_EPISODE if kind == "episode" else FILE_ROLE_EXTRA,
            commit=False,
        )
        if kind == "episode":
            if season_row is None:
                season_row = await repo.add_season(resource.id, season, sort_index=season, commit=False)
            await repo.add_episode(season_row.id, file_row.id, episode, sort_index=episode, commit=False)
        else:
            await repo.add_extra(resource.id, file_row.id, title=title or src.stem, sort_index=0, commit=False)
        imported += 1
    if imported:
        await repo.session.commit()
        logger.info("监视剧集增量入库: %s 个 → %s(%s)", imported, resource.title, type_.value)
        watch_events.record(type_.value)
    if skipped_dup:
        logger.info("监视剧集跳过（重复）: %s 个", skipped_dup)


HANDLERS: dict[ResourceType, WatchHandler] = {
    ResourceType.IMAGE: _import_files,
    ResourceType.VIDEO: _import_files,
    ResourceType.AUDIO: _import_files,
    ResourceType.NOVEL: _import_files,
    ResourceType.COMIC: _import_files,
    ResourceType.MODEL: _import_files,
    ResourceType.ANIME: _import_series,
    ResourceType.AV: _import_series,
}


class WatchBridge:
    """回调表 + 异步攒批消费任务。"""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[tuple[FileEvent, ResourceType]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def callbacks(self) -> dict[ResourceType, Callable[[FileEvent, ResourceType], None]]:
        """可监视类型的回调表（同一投递实现，类型由参数携带；处理差异在 HANDLERS）。"""
        return {type_: self._on_event for type_ in HANDLERS}

    def _on_event(self, event: FileEvent, type_: ResourceType) -> None:
        """worker 线程回调：只投递，不碰 DB。"""
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._queue.put_nowait, (event, type_))

    def start(self) -> None:
        """在事件循环线程内调用，捕获 loop 并启动消费任务。"""
        if self._task is None:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.create_task(self._consume())

    async def catch_up(self, dirs: dict[ResourceType, list[str]]) -> None:
        """补扫：后台未运行期间放进监视目录的文件，合成事件入队。

        已入库文件由导入管道的 sha256 查库去重跳过；未入库的自动导入。
        """
        total = 0
        for type_, paths in dirs.items():
            exts = File_Extension_Map.get(type_)
            if exts is None:
                continue
            for raw in paths:
                root = Path(raw)
                if not root.is_dir():
                    continue
                try:
                    files = await asyncio.to_thread(_walk_files, root, exts)
                except OSError as exc:
                    logger.warning("补扫目录失败 %s: %s", raw, exc)
                    continue
                for file in files:
                    await self._queue.put(
                        (
                            FileEvent(
                                type=EventType.CREATE,
                                path=file,
                                src_path=file,
                                is_directory=False,
                                resource_type=type_,
                            ),
                            type_,
                        )
                    )
                    total += 1
        if total:
            logger.info("监视目录补扫入队 %s 个文件", total)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _consume(self) -> None:
        while True:
            first = await self._queue.get()
            batch = [first]
            # 攒批窗口内继续收取，按类型分组后一次处理
            deadline = self._loop.time() + BATCH_WINDOW_SECONDS if self._loop else None
            while True:
                remaining = deadline - self._loop.time() if deadline is not None else 0
                if remaining <= 0:
                    break
                try:
                    batch.append(await asyncio.wait_for(self._queue.get(), timeout=remaining))
                except asyncio.TimeoutError:
                    break
            try:
                await self._handle_batch(batch)
            finally:
                for _ in batch:
                    self._queue.task_done()

    async def _handle_batch(self, batch: list[tuple[FileEvent, ResourceType]]) -> None:
        grouped: dict[ResourceType, list[FileEvent]] = {}
        for event, type_ in batch:
            if event.type == EventType.DELETE:
                logger.info("监视删除事件暂不处理: %s", event.path)
                continue
            grouped.setdefault(type_, []).append(event)
        for type_, events in grouped.items():
            handler = HANDLERS.get(type_)
            if handler is None:
                logger.info("无对应类型的监视处理器，跳过: %s 个 (%s)", len(events), type_.value)
                continue
            try:
                await handler(events, type_)
            except Exception as exc:  # noqa: BLE001 — 单组失败不拖垮消费循环
                logger.warning("监视处理失败 %s: %s", type_.value, exc)


# 进程级单例：main.py 与 settings service 共用
watch_bridge = WatchBridge()
