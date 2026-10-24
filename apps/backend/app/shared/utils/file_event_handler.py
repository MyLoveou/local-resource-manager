"""文件事件处理器：监视目录变化后对每个变化文件的回调处理（按资源类型派发）。

去重键按 (资源类型, 路径/哈希)：同一目录登记给多个类型时，各类型独立处理、互不阻断。
"""
from .file_watcher import (
    FileWatcher,
    FileEvent,
    EventType,
    resource_type_from_path,
)
from .calculateSHA256 import calculate_sha256_from_file
from .wait_until_stable import wait_until_stable
from ..log import logger
import queue
import threading
import os
from typing import Optional, Callable
from app.library.domain.models import ResourceType

# 内存结构限容（LRU：超出后逐出最旧项，防止长跑内存只增不减）
_PROCESSED_LIMIT = 10_000
_STAT_CACHE_LIMIT = 10_000
_SEEN_HASH_LIMIT = 50_000


def _evict_lru(cache: dict, limit: int) -> None:
    """dict 为插入序；超出上限逐出最旧键。"""
    while len(cache) > limit:
        cache.pop(next(iter(cache)))


class ShardedQueue:
    """按 key 路由到不同子队列，保证同 key 串行；同路径同类型未处理时合并（防抖）。"""

    def __init__(self, n: int, maxsize: int = 100):
        self.n = n
        self.queues = [queue.Queue(maxsize=maxsize) for _ in range(n)]
        self._pending: list[set[tuple[Optional[ResourceType], str]]] = [set() for _ in range(n)]
        self._locks = [threading.Lock() for _ in range(n)]

    def put(self, evt: FileEvent):
        idx = hash(evt.path) % self.n
        key = (evt.resource_type, evt.path)
        with self._locks[idx]:
            if key in self._pending[idx]:
                return  # 防抖：同路径同类型未处理时丢弃新事件（MODIFY 风暴合并）
            self._pending[idx].add(key)
        self.queues[idx].put(evt)

    def get(self, idx, timeout=None):
        evt = self.queues[idx].get(timeout=timeout)
        key = (evt.resource_type, evt.path)
        with self._locks[idx]:
            self._pending[idx].discard(key)
        return evt


class FileEventHandler:
    def __init__(
        self,
        watch_dirs: dict[ResourceType, list[str]],
        worker_count: int = 4,
        callbacks: Optional[dict[ResourceType, Callable[[FileEvent, ResourceType], None]]] = None,
        fallback: Optional[Callable[[FileEvent, ResourceType | None], None]] = None,
    ):
        self._stop = threading.Event()  # 停止事件，用于停止工作线程
        self._processed: dict[tuple[Optional[ResourceType], str], str] = (
            {}
        )  # (类型, 路径) → sha256，避免重复处理
        self.watch_dirs = watch_dirs
        self._callbacks: dict[ResourceType, Callable[[FileEvent, ResourceType], None]] = (
            callbacks or {}
        )  # 按资源类型分发的回调表
        self._fallback = fallback  # 未知/未配置类型的兜底回调
        self.file_watcher: Optional[FileWatcher] = None
        self.worker_count = worker_count  # 工作线程数量
        self.queue = ShardedQueue(
            worker_count
        )  # 分片队列，用于按文件路径哈希分配到不同的工作线程，保证同一文件的处理是串行的
        self.workers = []  # 记录工作线程列表
        self._stat_cache: dict[tuple[Optional[ResourceType], str], tuple[int, int]] = (
            {}
        )  # (类型, 路径) -> (mtime_ns, size)
        self._seen_hashes: dict[tuple[Optional[ResourceType], str], None] = {}  # (类型, sha256) 内容去重
        self._hash_lock = threading.Lock()  # 锁，用于保护 _seen_hashes 的并发访问

    def start(self):
        if self.file_watcher is not None:
            logger.warning("文件事件处理器已启动")
            return
        if not self.watch_dirs:
            logger.info("未配置监视目录，跳过启动文件监视器")
            return
        self.file_watcher = FileWatcher(watch_dirs=self.watch_dirs, queue=self.queue)
        self.file_watcher.start_watcher()
        for i in range(self.worker_count):
            # 启动工作线程
            t = threading.Thread(target=self._run_worker, args=(i,), daemon=True)
            t.start()
            self.workers.append(t)

    def stop(self):
        if self.file_watcher:
            self.file_watcher.stop_watcher()
        for q in self.queue.queues:
            q.join()  # 等待所有队列处理完

        self._stop.set()
        for worker in self.workers:
            worker.join(timeout=5)

    def _run_worker(self, idx: int) -> None:
        q: queue.Queue[FileEvent] = self.queue.queues[idx]
        while not self._stop.is_set():
            try:
                event: FileEvent = q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._process(event)
            except Exception as e:
                path = getattr(event, "path", repr(event))
                logger.error(f"处理失败 {path}: {e}")
            finally:
                q.task_done()

    def _process(self, event: FileEvent) -> None:
        path = event.path
        rt = event.resource_type

        # 1. 删除事件：清理状态 + 交给回调
        if event.type == EventType.DELETE:
            self._processed.pop((rt, path), None)
            self._stat_cache.pop((rt, path), None)
            self._dispatch(event)
            return

        # 2. 非文件（目录、已消失）跳过
        if not os.path.isfile(path):
            return

        # 3. 等文件写稳定，避免读到半个文件
        if not wait_until_stable(path):
            logger.debug(f"文件未稳定，跳过: {path}")
            return
        # ⭐ 快速检查：mtime + size 没变，直接跳过，不算 sha256
        try:
            st = os.stat(path)
        except OSError:
            return
        sig = (st.st_mtime_ns, st.st_size)
        if self._stat_cache.get((rt, path)) == sig:
            return
        self._stat_cache[(rt, path)] = sig
        _evict_lru(self._stat_cache, _STAT_CACHE_LIMIT)

        # 4. sha256 去重（按类型）；哈希结果写入事件供导入管道复用
        sha256 = calculate_sha256_from_file(path)
        if sha256 is None:
            return
        with self._hash_lock:
            if (rt, sha256) in self._seen_hashes:
                logger.info(f"文件 {path} 的 SHA256 已存在，跳过")
                self._processed[(rt, path)] = sha256
                _evict_lru(self._processed, _PROCESSED_LIMIT)
                return
            logger.info(f"文件 {path} 的 SHA256 {sha256}，处理")
            self._seen_hashes[(rt, sha256)] = None
            _evict_lru(self._seen_hashes, _SEEN_HASH_LIMIT)
            self._processed[(rt, path)] = sha256
            _evict_lru(self._processed, _PROCESSED_LIMIT)
        event.sha256 = sha256

        # 5. 回调（按资源类型派发）
        try:
            self._dispatch(event)
        except Exception:
            with self._hash_lock:
                # 回调失败，回滚 _processed，下次还能重试
                self._seen_hashes.pop((rt, sha256), None)
                self._processed.pop((rt, path), None)
            raise

    def _dispatch(self, event: FileEvent) -> None:
        """派发回调：事件携带类型优先，扩展名兜底；无匹配走 fallback。"""
        type_ = event.resource_type or resource_type_from_path(event.path)
        cb = self._callbacks.get(type_) if type_ is not None else None
        if cb is not None:
            cb(event, type_)
            return
        if self._fallback is not None:
            self._fallback(event, type_)
