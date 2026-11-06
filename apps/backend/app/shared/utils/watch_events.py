"""监视导入事件计数（供前端轮询检测新导入后自动刷新列表）。"""
from threading import Lock


class WatchEvents:
    """进程内单调递增修订号 + 最近导入类型。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._revision = 0
        self._last_type: str | None = None

    def record(self, type_value: str) -> None:
        with self._lock:
            self._revision += 1
            self._last_type = type_value

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {"revision": self._revision, "type": self._last_type}


watch_events = WatchEvents()
