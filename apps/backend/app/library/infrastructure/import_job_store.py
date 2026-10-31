"""进程内导入任务（单任务；进程退出即丢失）。"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field


@dataclass
class ImportJobState:
    """导入任务快照。"""

    id: str
    status: str = "queued"
    phase: str = "queued"
    total: int = 0
    done: int = 0
    percent: float = 0.0
    eta_seconds: int | None = None
    speed_mbps: float | None = None
    imported: int = 0
    skipped_duplicate: int = 0
    skipped_error: int = 0
    error: str | None = None
    message: str | None = None
    code: str | None = None
    details: list[str] = field(default_factory=list)


class ImportJobStore:
    """同时只允许一个 running。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._jobs: dict[str, ImportJobState] = {}
        self._running_id: str | None = None

    def get(self, job_id: str) -> ImportJobState | None:
        return self._jobs.get(job_id)

    def is_running(self) -> bool:
        return self._running_id is not None

    async def create_if_idle(self) -> ImportJobState | None:
        """已有运行中任务则 None。"""
        async with self._lock:
            if self._running_id is not None:
                return None
            job = ImportJobState(id=uuid.uuid4().hex, status="queued")
            self._jobs[job.id] = job
            self._running_id = job.id
            return job

    def mark_running(self, job: ImportJobState) -> None:
        job.status = "running"
        job.phase = "hash"

    async def finish(self, job: ImportJobState, *, failed: str | None = None) -> None:
        async with self._lock:
            job.status = "failed" if failed else "done"
            job.phase = "done" if not failed else "failed"
            job.error = failed
            if self._running_id == job.id:
                self._running_id = None


job_store = ImportJobStore()
