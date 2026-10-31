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


async def register_subtitle_file(
    session: AsyncSession,
    resources: Any,
    resource: Any,
    dest: Path,
    *,
    episode_id: int | None = None,
) -> Any:
    """把已复制进包内的字幕登记为文件行并建立关联，返回刷新后的资源。"""
    file_row = await resources.add_file(
        resource.id,
        path=str(dest),
        sha256=None,
        size=dest.stat().st_size,
        format_=dest.suffix.lower().lstrip("."),
        role=FILE_ROLE_SUBTITLE,
        commit=False,
    )
    await SubtitleRepository(session).attach(
        resource.id,
        file_row.id,
        episode_id=episode_id,
        language=infer_language(dest.name),
        title=dest.name,
        is_default=is_renderable(dest),
    )
    resource._touch()
    await resources.update(resource.id, resource, commit=False)
    await resources.commit()
    return await resources.get(resource.id)


_COVER_CONCURRENCY = 4


async def _extract_many(
    pending: list[tuple[Any, Path, str]],
) -> list[tuple[Any, Path, bool]]:
    """并发抽帧，返回 (row, dest, ok)；不碰数据库会话。"""
    if not pending:
        return []
    gate = asyncio.Semaphore(_COVER_CONCURRENCY)

    async def one(row: Any, video: Path, name: str) -> tuple[Any, Path, bool]:
        dest = video.parent / name
        if not video.is_file():
            return row, dest, False
        async with gate:
            ok = await asyncio.to_thread(
                extract_cover, video, dest, duration=row["duration"]
            )
        return row, dest, ok

    return list(
        await asyncio.gather(*(one(row, video, name) for row, video, name in pending))
    )


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


async def _extra_rows(session: AsyncSession, resource_id: int) -> list[Any]:
    result = await session.execute(
        text(
            "SELECT x.id AS extra_id, x.cover_file_id, "
            "       f.path AS video_path, f.duration "
            "FROM extras x JOIN files f ON f.id = x.file_id "
            "WHERE x.resource_id = :rid AND x.status = 'active' "
            "ORDER BY x.sort_index, x.id"
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
    """为每集抽帧封面。已有封面时跳过，除非 force。

    抽帧是 CPU/磁盘密集的（实测 0.47s/集），113 集串行要 50 秒以上，
    所以先并发抽帧、再串行写库（会话不是并发安全的）。
    """
    generated = skipped = failed = 0
    episode_rows = list(await _episode_rows(session, resource_id))
    pending = [
        (row, Path(str(row["video_path"])), f"ep{int(row['episode_number']):02d}-cover.jpg")
        for row in episode_rows
        if force or row["cover_file_id"] is None
    ]
    skipped += len(episode_rows) - len(pending)
    extracted = await _extract_many(pending)
    for row, dest, ok in extracted:
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

    extra_rows = list(await _extra_rows(session, resource_id))
    extra_pending = [
        (row, Path(str(row["video_path"])), f"extra{index:02d}-cover.jpg")
        for index, row in enumerate(extra_rows, start=1)
        if force or row["cover_file_id"] is None
    ]
    skipped += len(extra_rows) - len(extra_pending)
    for row, dest, ok in await _extract_many(extra_pending):
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
            text("UPDATE extras SET cover_file_id = :fid WHERE id = :xid"),
            {"fid": file_row.id, "xid": row["extra_id"]},
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
