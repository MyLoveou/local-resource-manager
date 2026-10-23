"""Short-lived AI jobs (model download / index build)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Awaitable, Callable


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    total: int = 0
    done: int = 0
    message: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @property
    def percent(self) -> int | None:
        if self.total <= 0:
            return None
        return max(0, min(100, round(self.done * 100 / self.total)))


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def create(self, kind: str, total: int = 0) -> Job:
        job = Job(id=uuid.uuid4().hex, kind=kind, total=total)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def has_active(self) -> bool:
        return any(job.status in {"queued", "running"} for job in self._jobs.values())

    def has_active_kind(self, kind: str) -> bool:
        return any(
            job.kind == kind and job.status in {"queued", "running"}
            for job in self._jobs.values()
        )

    def update(
        self,
        job: Job,
        *,
        status: str | None = None,
        total: int | None = None,
        done: int | None = None,
        message: str | None = None,
    ) -> None:
        if status is not None:
            job.status = status
        if total is not None:
            job.total = total
        if done is not None:
            job.done = done
        if message is not None:
            job.message = message
        job.updated_at = _now()

    def start(self, job: Job, runner: Callable[[Job], Awaitable[None]]) -> None:
        async def wrapped() -> None:
            self.update(job, status="running")
            try:
                await runner(job)
                self.update(job, status="done", message="完成")
            except Exception as exc:
                self.update(job, status="error", message=str(exc) or "任务失败")
            finally:
                self._tasks.discard(task)

        task = asyncio.create_task(wrapped())
        self._tasks.add(task)


jobs = JobManager()
