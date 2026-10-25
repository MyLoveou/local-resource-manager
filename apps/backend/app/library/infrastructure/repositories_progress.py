"""播放进度仓储（video-management S1）。

进度按 `file_id` 记：流媒体「集」挂在 `episodes.file_id` 上，
一个番剧作品 = 1 个 Resource + N 个 file，按资源记会让整部作品共用一个位置。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.infrastructure.orm import PlaybackProgressRow


class PlaybackProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, file_id: int) -> PlaybackProgressRow | None:
        row = await self.session.execute(
            select(PlaybackProgressRow).where(PlaybackProgressRow.file_id == file_id)
        )
        return row.scalars().first()

    async def file_belongs_to(self, resource_id: int, file_id: int) -> bool:
        found = await self.session.scalar(
            text("SELECT 1 FROM files WHERE id = :file_id AND resource_id = :resource_id"),
            {"file_id": file_id, "resource_id": resource_id},
        )
        return found is not None

    async def resource_status(self, resource_id: int) -> str | None:
        return await self.session.scalar(
            text("SELECT status FROM resources WHERE id = :id"), {"id": resource_id}
        )

    async def upsert(
        self,
        resource_id: int,
        file_id: int,
        position: float,
        duration: float | None,
        completed: bool,
    ) -> None:
        await self.session.execute(
            text(
                "INSERT INTO playback_progress "
                "(file_id, resource_id, position, duration, completed, updated_at) "
                "VALUES (:file_id, :resource_id, :position, :duration, :completed, datetime('now')) "
                "ON CONFLICT(file_id) DO UPDATE SET "
                "resource_id = excluded.resource_id, position = excluded.position, "
                "duration = excluded.duration, completed = excluded.completed, "
                "updated_at = datetime('now')"
            ),
            {
                "file_id": file_id,
                "resource_id": resource_id,
                "position": position,
                "duration": duration,
                "completed": 1 if completed else 0,
            },
        )
        await self.session.commit()

    async def delete(self, resource_id: int, file_id: int | None = None) -> int:
        stmt = delete(PlaybackProgressRow).where(
            PlaybackProgressRow.resource_id == resource_id
        )
        if file_id is not None:
            stmt = stmt.where(PlaybackProgressRow.file_id == file_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return int(result.rowcount or 0)

    def _resume_stmt(self, min_seconds: float, limit: int | None) -> tuple[Any, dict]:
        sql = (
            "SELECT p.file_id, p.resource_id, p.position, p.duration, p.updated_at, "
            "       r.title AS title, r.type AS type, r.cover_path AS cover_path, "
            "       s.season_number AS season_number, e.episode_number AS episode_number "
            "FROM playback_progress p "
            "JOIN resources r ON r.id = p.resource_id "
            "LEFT JOIN episodes e ON e.file_id = p.file_id "
            "LEFT JOIN seasons s ON s.id = e.season_id "
            "WHERE r.status = 'active' AND p.completed = 0 AND p.position >= :min_seconds "
            "ORDER BY p.updated_at DESC"
        )
        params: dict[str, Any] = {"min_seconds": min_seconds}
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = limit
        return text(sql), params

    async def list_resume(self, min_seconds: float, limit: int) -> list[Any]:
        stmt, params = self._resume_stmt(min_seconds, limit)
        result = await self.session.execute(stmt, params)
        return list(result.mappings().all())

    async def count_resume(self, min_seconds: float) -> int:
        total = await self.session.scalar(
            text(
                "SELECT COUNT(*) FROM playback_progress p "
                "JOIN resources r ON r.id = p.resource_id "
                "WHERE r.status = 'active' AND p.completed = 0 AND p.position >= :min_seconds"
            ),
            {"min_seconds": min_seconds},
        )
        return int(total or 0)
