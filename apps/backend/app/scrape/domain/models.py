"""抓取应用领域模型：抓取任务与候选。

流程：ScrapeJob（一次抓取）→ 多个 Candidate（候选列表）→ 用户确认 → 回填资源。
"""
from datetime import datetime
from enum import Enum

from pydantic import Field

from app.shared.errors import InvalidStateError
from app.shared.models import ApiModel


class ScrapeJobStatus(str, Enum):
    """抓取任务状态机。"""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ScrapeJob(ApiModel):
    """元数据抓取任务。

    状态机：queued → running → done / failed
    """

    id: int | None = None
    resource_id: int
    status: ScrapeJobStatus = ScrapeJobStatus.QUEUED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None  # 失败原因
    match_count: int = 0  # 命中候选数

    @property
    def is_terminal(self) -> bool:
        """是否已终止（done/failed）。"""
        return self.status in (ScrapeJobStatus.DONE, ScrapeJobStatus.FAILED)

    def start(self) -> None:
        """开始执行。仅 queued 状态合法。"""
        if self.status != ScrapeJobStatus.QUEUED:
            raise InvalidStateError(f"cannot start job from {self.status}")
        self.status = ScrapeJobStatus.RUNNING
        self.started_at = datetime.now()

    def finish(self, match_count: int = 0) -> None:
        """成功完成。仅 running 状态合法。"""
        if self.status != ScrapeJobStatus.RUNNING:
            raise InvalidStateError(f"cannot finish job from {self.status}")
        self.status = ScrapeJobStatus.DONE
        self.match_count = match_count
        self.finished_at = datetime.now()

    def fail(self, error: str) -> None:
        """失败。queued/running 均可进入。"""
        if self.is_terminal:
            raise InvalidStateError(f"cannot fail job from {self.status}")
        self.status = ScrapeJobStatus.FAILED
        self.error = error
        self.finished_at = datetime.now()


class Candidate(ApiModel):
    """抓取候选（搜索结果条目）。"""

    id: int | None = None
    job_id: int
    title: str
    url: str
    thumbnail_url: str | None = None
    source: str  # 来源适配器/站点标识（SearXNG / TMDB / Bangumi / 反查图…）
    relevance: float | None = None  # 相关度 0-1
    selected: bool = False  # 用户是否选中回填
    created_at: datetime | None = Field(default_factory=datetime.now)

    def select(self) -> None:
        """标记为用户选中。"""
        self.selected = True

    def unselect(self) -> None:
        """取消选中。"""
        self.selected = False
