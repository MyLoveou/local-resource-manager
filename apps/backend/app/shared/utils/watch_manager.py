"""监视器管理器：设置保存后整体重启文件监视器。

- main.py lifespan 实例化并 apply 启动配置；退出时 shutdown
- settings service 在保存后调用 apply 重配
"""
from __future__ import annotations

from threading import Lock
from typing import Callable, Optional

from app.library.domain.models import ResourceType
from app.shared.log import logger
from app.shared.utils.file_event_handler import FileEventHandler
from app.shared.utils.file_watcher import FileEvent

WatchCallback = Callable[[FileEvent, ResourceType], None]


class WatchManager:
    """持有当前 FileEventHandler；apply(dirs) = 停旧起新。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._handler: Optional[FileEventHandler] = None
        self._dirs: dict[ResourceType, list[str]] = {}
        self._callbacks: Optional[dict[ResourceType, WatchCallback]] = None

    def apply(
        self,
        dirs: dict[ResourceType, list[str]],
        callbacks: Optional[dict[ResourceType, WatchCallback]] = None,
    ) -> None:
        """按新配置重启监视器（空配置 = 停止监视）。

        首次 apply 传入 callbacks 后被记住；后续重配（如设置保存）无需再传。
        """
        with self._lock:
            if callbacks is not None:
                self._callbacks = callbacks
            old = self._handler
            if old is not None:
                try:
                    old.stop()
                except Exception:  # noqa: BLE001 — 停旧失败不阻断起新
                    logger.exception("停止旧监视器失败")
            self._dirs = dict(dirs)
            self._handler = FileEventHandler(watch_dirs=self._dirs, callbacks=self._callbacks)
            if self._dirs:
                self._handler.start()
                logger.info("监视器已按新配置启动: %s", self._dirs)
            else:
                logger.info("监视目录为空，监视器未启动")

    def shutdown(self) -> None:
        with self._lock:
            if self._handler is not None:
                self._handler.stop()
                self._handler = None


# 进程级单例：main.py 与 settings service 共用
watch_manager = WatchManager()
