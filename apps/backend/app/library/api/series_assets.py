"""每集封面与字幕的接口。"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.series_assets import generate_episode_covers
from app.library.application.subtitles import infer_language, is_renderable
from app.library.domain.media_types import FILE_ROLE_SUBTITLE
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


class SubtitleAttachRequest(BaseModel):
    file_path: str
    episode_id: int | None = None


class BackfillResult(BaseModel):
    generated: int = 0
    skipped: int = 0
    failed: int = 0


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


@router.post("/resources/{resource_id}/subtitles", response_model=SubtitleItem)
async def attach_subtitle(
    resource_id: int,
    body: SubtitleAttachRequest,
    session: AsyncSession = Depends(get_session),
) -> SubtitleItem:
    """把一个本地字幕文件复制进库并挂到指定集（或资源级）。"""
    source = Path(body.file_path)
    if not source.is_file():
        raise FileNotFoundError(body.file_path)

    # 放到该集视频同目录的 subs/ 下，保持「一集一目录」的结构
    parent_row = (
        await session.execute(
            text(
                "SELECT f.path FROM episodes e JOIN files f ON f.id = e.file_id "
                "WHERE e.id = :eid"
            ),
            {"eid": body.episode_id},
        )
    ).first() if body.episode_id else None
    if parent_row is not None:
        base = Path(str(parent_row[0])).parent
    else:
        base = Path(str((await session.execute(
            text("SELECT path FROM files WHERE resource_id = :rid AND role = 'primary' LIMIT 1"),
            {"rid": resource_id},
        )).scalar() or ".")).parent
    dest = base / "subs" / source.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        await asyncio.to_thread(shutil.copy2, source, dest)

    resources = ResourceRepository(session)
    file_row = await resources.add_file(
        resource_id,
        path=str(dest),
        sha256=None,
        size=dest.stat().st_size,
        format_=source.suffix.lstrip(".").lower(),
        role=FILE_ROLE_SUBTITLE,
        commit=False,
    )
    await SubtitleRepository(session).attach(
        resource_id,
        file_row.id,
        episode_id=body.episode_id,
        language=infer_language(source.name),
        title=source.name,
        is_default=is_renderable(source),
    )
    await session.commit()
    return SubtitleItem(
        id=int(file_row.id),
        episode_id=body.episode_id,
        file_id=int(file_row.id),
        label=source.name,
        language=infer_language(source.name),
        renderable=is_renderable(source),
        format=source.suffix.lstrip(".").lower(),
        url=file_content_url(resource_id, int(file_row.id)),
    )


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
        result = await generate_episode_covers(
            session, resources, resource_id, force=force
        )
    except Exception as exc:  # noqa: BLE001 - 抽帧失败不该 500
        logger.warning("补封面失败 resource=%s: %s", resource_id, exc)
        return BackfillResult(generated=0, skipped=0, failed=1)
    return BackfillResult(**result)
