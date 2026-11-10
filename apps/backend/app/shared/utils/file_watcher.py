"""文件监视器：按资源类型分组注册目录，事件携带类型。

- 监听目录按资源类型配置：一个类型可多个目录；同一目录可被多个类型登记（各自回调都收到）。
- 事件类型由目录声明；文件扩展名必须在对应类型的映射表内才派发（B 方案：目录类型 + 扩展名过滤）。
"""

from enum import Enum
from typing import Callable, Optional
from dataclasses import dataclass
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from app.library.domain.type_profile import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    NOVEL_EXTENSIONS,
    MODEL_EXTENSIONS,
    COMIC_EXTENSIONS,
)
from app.library.domain.models import ResourceType
from ..log import logger
import queue

# 资源类型对应文件扩展名映射
File_Extension_Map = {
    ResourceType.AUDIO: AUDIO_EXTENSIONS,
    ResourceType.VIDEO: VIDEO_EXTENSIONS,
    ResourceType.IMAGE: IMAGE_EXTENSIONS,
    ResourceType.NOVEL: NOVEL_EXTENSIONS,
    ResourceType.MODEL: MODEL_EXTENSIONS,
    ResourceType.COMIC: COMIC_EXTENSIONS,
    # 剧集型：目录内是视频文件（扩展名同视频）
    ResourceType.ANIME: VIDEO_EXTENSIONS,
    ResourceType.AV: VIDEO_EXTENSIONS,
}


def file_extension_from_type(type_: ResourceType) -> frozenset[str]:
    return File_Extension_Map[type_]


def resource_type_from_path(path: str) -> Optional[ResourceType]:
    """按扩展名反查资源类型；未知扩展名返回 None。"""
    suffix = Path(path).suffix.lower()  # 保留点，与类型映射的 ".jpg" 一致
    for type_, exts in File_Extension_Map.items():
        if suffix in exts:
            return type_
    return None


def extension_matches_type(type_: ResourceType, path: str) -> bool:
    """文件扩展名是否在该类型的映射表内（目录类型 + 扩展名过滤）。"""
    return Path(path).suffix.lower() in File_Extension_Map[type_]


class EventType(str, Enum):
    CREATE = "create"
    DELETE = "delete"
    MODIFY = "modify"
    MOVE = "move"


@dataclass
class FileEvent:
    type: EventType
    path: str  # 目标路径，moved时是dest_path
    src_path: str  # 原始路径，仅在移动事件中使用
    is_directory: bool  # 是否是目录
    resource_type: Optional[ResourceType] = None  # 由监视目录声明；多类型目录会发多条事件
    sha256: Optional[str] = None  # 由处理器预计算的哈希，供导入管道复用（避免二次全量哈希）


class FileWatcherHandler(FileSystemEventHandler):
    """处理文件变化的处理器。"""

    def __init__(self, queue: queue.Queue, types_for: Callable[[str], list[ResourceType]]):
        self.queue = queue
        self._types_for = types_for

    def _put(self, event: FileSystemEvent, type_: EventType):
        if event.is_directory:
            return
        path = getattr(event, "dest_path", None) or event.src_path
        for resource_type in self._types_for(path):
            evt = FileEvent(
                type=type_,
                path=path,
                src_path=event.src_path,
                is_directory=event.is_directory,
                resource_type=resource_type,
            )
            logger.info("文件事件: %s - %s (%s)", type_, path, resource_type.value)
            self.queue.put(evt)

    def on_created(self, event: FileSystemEvent, async_callback: Optional[Callable] = None):
        logger.info("文件创建: %s", event.src_path)
        self._put(event, EventType.CREATE)

    def on_deleted(self, event: FileSystemEvent, async_callback: Optional[Callable] = None):
        logger.info("文件删除: %s", event.src_path)
        self._put(event, EventType.DELETE)

    def on_modified(self, event: FileSystemEvent, async_callback: Optional[Callable] = None):
        logger.info("文件修改: %s", event.src_path)
        self._put(event, EventType.MODIFY)

    def on_moved(self, event: FileSystemEvent, async_callback: Optional[Callable] = None):
        logger.info("文件移动: %s", event.src_path)
        self._put(event, EventType.MOVE)


class FileWatcher:
    def __init__(
        self,
        watch_dirs: dict[ResourceType, list[str]],
        queue: queue.Queue,
    ):
        self.watch_dirs = watch_dirs  # 资源类型 → 监视目录列表
        self.queue = queue  # 队列，用于存放触发了监听的文件路径
        self.handler = FileWatcherHandler(self.queue, self._types_for)  # 处理器
        self.observer = Observer()  # 观察者
        self._stopped = False  # 记录是否已停止
        # 解析后的目录 → 类型列表（同一目录可被多个类型登记）
        self._dir_types: dict[str, list[ResourceType]] = {}
        self._watched_paths: set[str] = set()  # 已 schedule 的目录，避免重复注册

    def _types_for(self, path: str) -> list[ResourceType]:
        """路径归属类型：最长前缀匹配注册目录，再按扩展名过滤。"""
        p = Path(path).resolve()
        best_len = -1
        best: list[ResourceType] = []
        for dir_path, types in self._dir_types.items():
            d = Path(dir_path)
            try:
                if d == p or d in p.parents:
                    if len(dir_path) > best_len:
                        best_len = len(dir_path)
                        best = types
            except ValueError:
                continue  # 不同盘符不可比
        return [t for t in best if extension_matches_type(t, path)]

    def start_watcher(self):
        for type_, dirs in self.watch_dirs.items():
            for watch_dir in dirs:
                resolved = str(Path(watch_dir).resolve())
                registered = self._dir_types.setdefault(resolved, [])
                if type_ not in registered:
                    registered.append(type_)
                if resolved not in self._watched_paths:
                    self.observer.schedule(self.handler, resolved, recursive=True)
                    self._watched_paths.add(resolved)
                    logger.info("监视的目录: %s (%s)", resolved, type_.value)
        self.observer.start()

    def stop_watcher(self):
        if getattr(self, "_stopped", False):
            return
        self._stopped = True
        self.observer.stop()
        self.observer.join()
        logger.info("文件监视器已停止")
