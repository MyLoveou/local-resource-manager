"""导入收尾的系列资源装配：每集封面抽帧 + 字幕登记。

两条路径共用同一套函数：
- 导入后立即执行（一次性把封面和字幕补齐）
- 之后按资源补（`force` 重抽，只补缺失）
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.episode_covers import extract_cover
from app.library.application.subtitles import (
    discover_subtitles,
    infer_language,
    is_renderable,
    match_all,
)
from app.library.domain.media_types import (
    FILE_ROLE_EPISODE_COVER,
    FILE_ROLE_SUBTITLE,
)
from app.library.infrastructure.repositories_subtitles import SubtitleRepository
from app.shared.log import logger


async def _episode_rows(session: AsyncSession, resource_id: int) -> list[Any]:
    result = await session.execute(
        text(
            "SELECT e.id AS episode_id, e.episode_number, e.cover_file_id, "
            "       f.path AS video_path, f.duration "
            "FROM episodes e "
            "JOIN seasons s ON s.id = e.season_id "
            "JOIN files f ON f.id = e.file_id "
            "WHERE s.resource_id = :rid AND e.status = 'active' "
            "ORDER BY s.season_number, e.episode_number"
        ),
        {"rid": resource_id},
    )
    return list(result.mappings().all())


async def generate_episode_covers(
    session: AsyncSession,
    resources: Any,
    resource_id: int,
    *,
    force: bool = False,
) -> dict[str, int]:
    """为每集抽帧封面。已有封面时跳过，除非 force。"""
    generated = skipped = failed = 0
    for row in await _episode_rows(session, resource_id):
        if row["cover_file_id"] is not None and not force:
            skipped += 1
            continue
        video = Path(str(row["video_path"]))
        if not video.is_file():
            failed += 1
            continue
        dest = video.parent / f"ep{int(row['episode_number']):02d}-cover.jpg"
        ok = await asyncio.to_thread(
            extract_cover, video, dest, duration=row["duration"]
        )
        if not ok:
            failed += 1
            continue
        file_row = await resources.add_file(
            resource_id,
            path=str(dest),
            sha256=None,
            size=dest.stat().st_size,
            format_="jpg",
            role=FILE_ROLE_EPISODE_COVER,
            commit=False,
        )
        await session.execute(
            text("UPDATE episodes SET cover_file_id = :fid WHERE id = :eid"),
            {"fid": file_row.id, "eid": row["episode_id"]},
        )
        generated += 1
    await session.commit()
    return {"generated": generated, "skipped": skipped, "failed": failed}


async def register_subtitles(
    session: AsyncSession,
    resources: Any,
    resource_id: int,
    root: Path,
) -> int:
    """扫描源目录字幕，按集号/相似度挂到对应集上；返回挂载条数。"""
    candidates = await asyncio.to_thread(discover_subtitles, root)
    if not candidates:
        return 0

    rows = await _episode_rows(session, resource_id)
    videos = {Path(str(row["video_path"])): row for row in rows}

    # 用**源视频文件名**匹配，而不是包内重命名后的路径
    matched = match_all(list(videos.keys()), candidates)
    repo = SubtitleRepository(session)
    attached = 0
    for video_path, subtitle_paths in matched.items():
        episode = videos.get(video_path)
        if episode is None:
            continue
        for subtitle in subtitle_paths:
            dest = video_path.parent / "subs" / subtitle.name
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    await asyncio.to_thread(shutil.copy2, subtitle, dest)
            except OSError as exc:
                logger.warning("字幕复制失败 %s: %s", subtitle, exc)
                continue
            file_row = await resources.add_file(
                resource_id,
                path=str(dest),
                sha256=None,
                size=dest.stat().st_size,
                format_=subtitle.suffix.lstrip(".").lower(),
                role=FILE_ROLE_SUBTITLE,
                commit=False,
            )
            await repo.attach(
                resource_id,
                file_row.id,
                episode_id=episode["episode_id"],
                language=infer_language(subtitle.name),
                title=subtitle.name,
                is_default=is_renderable(subtitle),
            )
            attached += 1
    await session.commit()
    return attached
