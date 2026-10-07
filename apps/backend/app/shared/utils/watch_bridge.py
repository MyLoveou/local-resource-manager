"""监视事件 → 导入用例的线程/异步桥。

- worker 线程回调只投递事件（call_soon_threadsafe），不碰 DB
- 处理层按资源类型**显式映射**（HANDLERS）：新增类型/差异化处理只加映射项
- file 型攒批（同类型事件合并一次导入管道，内部并发）；sha256 复用事件预计算值
- 监视导入默认不入刮削队列（auto_scrape=False）
- 剧集型（anime/av）自动导入未接入：需要目录级上下文，占位 handler
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Awaitable, Callable

from app.library.application.import_service import ImportService
from app.library.domain.models import ResourceType
from app.library.infrastructure.import_job_store import ImportJobState
from app.shared.db.db import get_session_factory
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


async def _defer_series(events: list[FileEvent], type_: ResourceType) -> None:
    """剧集型占位：自动导入未接入（需要目录级上下文，后续立项换实现）。"""
    for event in events:
        logger.info("%s 监视目录自动导入未接入，跳过: %s", type_.value, event.path)


HANDLERS: dict[ResourceType, WatchHandler] = {
    ResourceType.IMAGE: _import_files,
    ResourceType.VIDEO: _import_files,
    ResourceType.AUDIO: _import_files,
    ResourceType.NOVEL: _import_files,
    ResourceType.COMIC: _import_files,
    ResourceType.MODEL: _import_files,
    ResourceType.ANIME: _defer_series,
    ResourceType.AV: _defer_series,
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
