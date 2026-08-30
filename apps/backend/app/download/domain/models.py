"""下载应用领域模型：下载任务。

任务状态权威存于本表（编排层原则），aria2/rqbit 仅作为执行引擎。
"""
from datetime import datetime
from enum import Enum

from app.shared.constants import PROTOCOL_TO_ENGINE, DownloadEngine, Protocol
from app.shared.errors import InvalidStateError
from app.shared.models import ApiModel
from app.shared.value_objects import Progress


class DownloadStatus(str, Enum):
    """下载任务状态机。"""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class DownloadTask(ApiModel):
    """下载任务。

    状态机：queued → running ⇄ paused → done / failed
    状态权威存于本表（编排层原则），aria2/rqbit 仅作为执行引擎。
    """

    id: int | None = None
    url: str
    protocol: Protocol = Protocol.HTTP
    engine: DownloadEngine = DownloadEngine.ARIA2
    status: DownloadStatus = DownloadStatus.QUEUED
    save_path: str | None = None
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed: int = 0  # 字节/秒
    error: str | None = None  # 失败原因
    target_resource_id: int | None = None  # 完成入库后关联的资源
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def is_terminal(self) -> bool:
        """是否已终止（done/failed）。"""
        return self.status in (DownloadStatus.DONE, DownloadStatus.FAILED)

    @property
    def progress(self) -> Progress:
        """进度值对象（只读视图，替代散字段计算）。"""
        return Progress(
            downloaded=self.downloaded_bytes,
            total=self.total_bytes,
            speed=self.speed,
        )

    @property
    def percent(self) -> float | None:
        """下载进度百分比 0-100。总量未知时返回 None。"""
        return self.progress.percent

    @staticmethod
    def default_engine_for(protocol: Protocol) -> DownloadEngine:
        """根据协议返回默认引擎（引用常量路由表）。"""
        return PROTOCOL_TO_ENGINE.get(protocol, DownloadEngine.ARIA2)

    def _transition(self, target: DownloadStatus, *allowed: DownloadStatus) -> None:
        if self.status not in allowed:
            raise InvalidStateError(f"cannot go {self.status} → {target}")
        self.status = target
        self.updated_at = datetime.now()

    def start(self) -> None:
        """开始/恢复执行。queued / paused 均可进入 running。"""
        self._transition(DownloadStatus.RUNNING, DownloadStatus.QUEUED, DownloadStatus.PAUSED)

    def pause(self) -> None:
        """暂停。仅 running 合法。"""
        self._transition(DownloadStatus.PAUSED, DownloadStatus.RUNNING)

    def resume(self) -> None:
        """恢复。仅 paused 合法。"""
        self._transition(DownloadStatus.RUNNING, DownloadStatus.PAUSED)

    def mark_done(self) -> None:
        """完成。running / queued 可进入。"""
        self._transition(DownloadStatus.DONE, DownloadStatus.RUNNING, DownloadStatus.QUEUED)

    def mark_failed(self, error: str) -> None:
        """失败。queued / running / paused 可进入。"""
        self._transition(DownloadStatus.FAILED, DownloadStatus.QUEUED, DownloadStatus.RUNNING, DownloadStatus.PAUSED)
        self.error = error

    def report_progress(self, downloaded: int, total: int | None = None, speed: int = 0) -> None:
        """进度上报（由引擎事件驱动）。"""
        self.downloaded_bytes = downloaded
        if total is not None:
            self.total_bytes = total
        self.speed = speed
