"""subtitle_tracks 的读写（字幕与集/资源的关联）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SubtitleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def attach(
        self,
        resource_id: int,
        file_id: int,
        *,
        episode_id: int | None = None,
        language: str | None = None,
        title: str | None = None,
        is_default: bool = False,
        sort_index: int = 0,
    ) -> None:
        """挂载字幕；同一 (file, episode) 重复挂载是幂等的。"""
        await self.session.execute(
            text(
                "INSERT OR IGNORE INTO subtitle_tracks "
                "(resource_id, file_id, episode_id, language, title, is_default, sort_index) "
                "VALUES (:rid, :fid, :eid, :lang, :title, :default, :sort)"
            ),
            {
                "rid": resource_id,
                "fid": file_id,
                "eid": episode_id,
                "lang": language,
                "title": title,
                "default": 1 if is_default else 0,
                "sort": sort_index,
            },
        )

    async def list_for_resource(self, resource_id: int) -> list[Any]:
        result = await self.session.execute(
            text(
                "SELECT t.id, t.file_id, t.episode_id, t.language, t.title, t.is_default, "
                "       f.path, f.format "
                "FROM subtitle_tracks t JOIN files f ON f.id = t.file_id "
                "WHERE t.resource_id = :rid "
                "ORDER BY t.episode_id IS NULL, t.episode_id, t.sort_index, t.id"
            ),
            {"rid": resource_id},
        )
        return list(result.mappings().all())

    async def list_for_episode(self, episode_id: int) -> list[Any]:
        result = await self.session.execute(
            text(
                "SELECT t.id, t.file_id, t.language, t.title, t.is_default, f.path, f.format "
                "FROM subtitle_tracks t JOIN files f ON f.id = t.file_id "
                "WHERE t.episode_id = :eid ORDER BY t.sort_index, t.id"
            ),
            {"eid": episode_id},
        )
        return list(result.mappings().all())

    async def detach(self, track_id: int) -> bool:
        """只解除关联，不删除字幕文件本身。"""
        result = await self.session.execute(
            text("DELETE FROM subtitle_tracks WHERE id = :id"), {"id": track_id}
        )
        return bool(result.rowcount)
