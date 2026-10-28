"""每集封面与字幕的接口。

字幕的新增复用 `POST /library/resources/{id}/subtitles`（那里已按视频语义处理
文件名），本模块只提供：字幕列表、解除关联、补封面、手动换单集封面。
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.series_assets import generate_episode_covers
from app.library.application.subtitles import is_renderable
from app.library.domain.media_types import FILE_ROLE_EPISODE_COVER
from app.library.infrastructure.media_paths import file_content_url
from app.library.infrastructure.repositories import ResourceRepository
from app.library.infrastructure.repositories_subtitles import SubtitleRepository
from app.shared.db.db import get_session
from app.shared.log import logger

router = APIRouter(tags=["library-series-assets"])


class SubtitleItem(BaseModel):
    id: int
    episode_id: int | None = None
    file_id: int
    label: str
    language: str | None = None
    renderable: bool = False
    format: str | None = None
    url: str


class BackfillResult(BaseModel):
    generated: int = 0
    skipped: int = 0
    failed: int = 0


class EpisodeCoverUpdate(BaseModel):
    """手动换封面：给图片路径，或 clear=true 回退作品封面。"""

    image_path: str | None = None
    clear: bool = False


@router.get("/resources/{resource_id}/subtitles", response_model=list[SubtitleItem])
async def list_subtitles(
    resource_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[SubtitleItem]:
    rows = await SubtitleRepository(session).list_for_resource(resource_id)
    return [
        SubtitleItem(
            id=int(row["id"]),
            episode_id=row["episode_id"],
            file_id=int(row["file_id"]),
            label=str(row["title"] or Path(str(row["path"])).name),
            language=row["language"],
            renderable=is_renderable(Path(str(row["path"]))),
            format=row["format"],
            url=file_content_url(resource_id, int(row["file_id"])),
        )
        for row in rows
    ]


@router.delete("/subtitles/{track_id}")
async def detach_subtitle(
    track_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    ok = await SubtitleRepository(session).detach(track_id)
    await session.commit()
    return {"deleted": ok}


@router.post("/resources/{resource_id}/covers/backfill", response_model=BackfillResult)
async def backfill_covers(
    resource_id: int,
    force: bool = False,
    session: AsyncSession = Depends(get_session),
) -> BackfillResult:
    resources = ResourceRepository(session)
    try:
        result = await generate_episode_covers(session, resources, resource_id, force=force)
    except Exception as exc:  # noqa: BLE001 - 抽帧失败不该 500
        logger.warning("补封面失败 resource=%s: %s", resource_id, exc)
        return BackfillResult(generated=0, skipped=0, failed=1)
    return BackfillResult(**result)


@router.put("/episodes/{episode_id}/cover")
async def update_episode_cover(
    episode_id: int,
    body: EpisodeCoverUpdate,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    row = (
        await session.execute(
            text(
                "SELECT e.id, e.episode_number, s.resource_id, f.path AS video_path "
                "FROM episodes e "
                "JOIN seasons s ON s.id = e.season_id "
                "JOIN files f ON f.id = e.file_id "
                "WHERE e.id = :eid"
            ),
            {"eid": episode_id},
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="episode not found")

    if body.clear:
        await session.execute(
            text("UPDATE episodes SET cover_file_id = NULL WHERE id = :eid"),
            {"eid": episode_id},
        )
        await session.commit()
        return {"cleared": True}

    if not body.image_path:
        raise HTTPException(status_code=400, detail="image_path required")
    source = Path(body.image_path)
    if not source.is_file():
        raise HTTPException(status_code=400, detail="image not found")

    dest = Path(str(row[2])).parent / f"ep{int(row[1]):02d}-cover{source.suffix.lower()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(shutil.copy2, source, dest)

    resources = ResourceRepository(session)
    file_row = await resources.add_file(
        int(row[2]),
        path=str(dest),
        sha256=None,
        size=dest.stat().st_size,
        format_=source.suffix.lstrip(".").lower(),
        role=FILE_ROLE_EPISODE_COVER,
        commit=False,
    )
    await session.execute(
        text("UPDATE episodes SET cover_file_id = :fid WHERE id = :eid"),
        {"fid": file_row.id, "eid": episode_id},
    )
    await session.commit()
    return {"coverUrl": file_content_url(int(row[2]), int(file_row.id))}
