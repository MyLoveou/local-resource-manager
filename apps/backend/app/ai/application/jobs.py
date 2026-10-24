"""Short-lived AI jobs (model download / index build)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Awaitable, Callable

from app.shared.log import logger


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    total: int = 0
    done: int = 0
    failed: int = 0
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
        self._persist_tasks: set[asyncio.Task[None]] = set()
        self._persist_hook: Callable[[Job], Awaitable[None]] | None = None

    def set_persister(self, hook: Callable[[Job], Awaitable[None]]) -> None:
        self._persist_hook = hook

    def _schedule_persist(self, job: Job) -> None:
        if self._persist_hook is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(self._persist_hook(job))
        self._persist_tasks.add(task)

        def done(completed: asyncio.Task[None]) -> None:
            self._persist_tasks.discard(completed)
            try:
                completed.result()
            except Exception:
                logger.warning("Failed to persist AI job %s", job.id, exc_info=True)

        task.add_done_callback(done)

    def create(self, kind: str, total: int = 0) -> Job:
        job = Job(id=uuid.uuid4().hex, kind=kind, total=total)
        self._jobs[job.id] = job
        self._schedule_persist(job)
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

    def recent(self, limit: int = 20) -> list[Job]:
        return sorted(
            self._jobs.values(), key=lambda item: item.created_at, reverse=True
        )[: max(1, min(limit, 100))]

    def update(
        self,
        job: Job,
        *,
        status: str | None = None,
        total: int | None = None,
        done: int | None = None,
        failed: int | None = None,
        message: str | None = None,
    ) -> None:
        if status is not None:
            job.status = status
        if total is not None:
            job.total = total
        if done is not None:
            job.done = done
        if failed is not None:
            job.failed = failed
        if message is not None:
            job.message = message
        job.updated_at = _now()
        if status is not None:
            self._schedule_persist(job)

    def start(self, job: Job, runner: Callable[[Job], Awaitable[None]]) -> None:
        async def wrapped() -> None:
            self.update(job, status="running")
            try:
                await runner(job)
                self.update(job, status="done", message=job.message or "完成")
            except Exception as exc:
                self.update(job, status="error", message=str(exc) or "任务失败")
            finally:
                self._tasks.discard(task)

        task = asyncio.create_task(wrapped())
        self._tasks.add(task)


jobs = JobManager()
