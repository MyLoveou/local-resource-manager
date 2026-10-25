"""播放进度用例（video-management S1）。

阈值（D-20261025-01 · Q2）：低于 10 秒不记；达到 95% 视为看完，位置归零。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.library.application.schemas import (
    PlaybackProgressOut,
    ResumeItem,
    ResumePage,
)
from app.library.infrastructure.media_paths import media_path
from app.library.infrastructure.repositories_progress import PlaybackProgressRepository

MIN_RECORD_SECONDS = 10.0
COMPLETE_RATIO = 0.95


@dataclass(frozen=True)
class NormalizedProgress:
    position: float
    completed: bool
    skip: bool


def normalize_progress(
    position: float | None,
    duration: float | None,
    *,
    has_existing: bool,
) -> NormalizedProgress:
    """把原始上报收成可落库的进度。

    - 负值归零
    - 有 duration 且已播到 95% → completed，位置归零（下次从头开始）
    - 没有历史且不足 10 秒 → 丢弃（避免误点写入噪音）
    """
    pos = max(0.0, float(position or 0.0))
    if duration and duration > 0 and pos / float(duration) >= COMPLETE_RATIO:
        return NormalizedProgress(position=0.0, completed=True, skip=False)
    if not has_existing and pos < MIN_RECORD_SECONDS:
        return NormalizedProgress(position=pos, completed=False, skip=True)
    return NormalizedProgress(position=pos, completed=False, skip=False)


def _to_out(row) -> PlaybackProgressOut:
    return PlaybackProgressOut(
        file_id=int(row.file_id),
        resource_id=int(row.resource_id),
        position=float(row.position or 0.0),
        duration=row.duration,
        completed=bool(row.completed),
        updated_at=row.updated_at,
    )


def _percent(position: float, duration: float | None) -> float:
    if not duration or duration <= 0:
        return 0.0
    return round(min(100.0, max(0.0, position / float(duration) * 100.0)), 1)


class ProgressService:
    def __init__(self, repository: PlaybackProgressRepository) -> None:
        self._repo = repository

    async def record(
        self,
        resource_id: int,
        file_id: int,
        position: float | None,
        duration: float | None,
    ) -> PlaybackProgressOut | None:
        status = await self._repo.resource_status(resource_id)
        if status != "active":
            return None
        if not await self._repo.file_belongs_to(resource_id, file_id):
            return None
        existing = await self._repo.get(file_id)
        normalized = normalize_progress(
            position, duration, has_existing=existing is not None
        )
        if normalized.skip:
            return None
        await self._repo.upsert(
            resource_id,
            file_id,
            normalized.position,
            duration,
            normalized.completed,
        )
        row = await self._repo.get(file_id)
        return _to_out(row) if row is not None else None

    async def get(self, resource_id: int, file_id: int) -> PlaybackProgressOut | None:
        if not await self._repo.file_belongs_to(resource_id, file_id):
            return None
        row = await self._repo.get(file_id)
        return _to_out(row) if row is not None else None

    async def clear(self, resource_id: int, file_id: int | None = None) -> int:
        return await self._repo.delete(resource_id, file_id)

    async def resume(self, limit: int = 20) -> ResumePage:
        rows = await self._repo.list_resume(MIN_RECORD_SECONDS, limit)
        items = [
            ResumeItem(
                resource_id=int(row["resource_id"]),
                file_id=int(row["file_id"]),
                title=str(row["title"] or ""),
                type=str(row["type"] or ""),
                cover_path=media_path(row["cover_path"]),
                position=float(row["position"] or 0.0),
                duration=row["duration"],
                percent=_percent(float(row["position"] or 0.0), row["duration"]),
                season_number=row["season_number"],
                episode_number=row["episode_number"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
        total = await self._repo.count_resume(MIN_RECORD_SECONDS)
        return ResumePage(items=items, total=total)
