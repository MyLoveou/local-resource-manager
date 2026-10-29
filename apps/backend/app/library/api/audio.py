"""音轨枚举与按轨播放。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.audio_tracks import ensure_remuxed_async, list_audio_tracks
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.config import settings
from app.shared.db.db import get_session
from app.shared.media_auth import sign_media_path

router = APIRouter(tags=["library-audio"])


class AudioTrackItem(BaseModel):
    index: int
    label: str
    language: str | None = None
    codec: str | None = None
    channels: int | None = None
    url: str


def _stream_path(resource_id: int, file_id: int, index: int) -> str:
    raw = f"/library/resources/{resource_id}/files/{file_id}/audio/{index}"
    return sign_media_path(raw) or raw


@router.get(
    "/resources/{resource_id}/files/{file_id}/audio-tracks",
    response_model=list[AudioTrackItem],
)
async def audio_tracks(
    resource_id: int,
    file_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[AudioTrackItem]:
    row = await ResourceRepository(session).get_file(resource_id, file_id)
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    tracks = await asyncio.to_thread(list_audio_tracks, Path(str(row.path)))
    return [
        AudioTrackItem(
            index=int(track["index"]),
            label=str(track["label"]),
            language=track["language"],
            codec=track["codec"],
            channels=track["channels"],
            url=_stream_path(resource_id, file_id, int(track["index"])),
        )
        for track in tracks
    ]


@router.get("/resources/{resource_id}/files/{file_id}/audio/{index}")
async def audio_stream(
    resource_id: int,
    file_id: int,
    index: int,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    row = await ResourceRepository(session).get_file(resource_id, file_id)
    if row is None:
        raise HTTPException(status_code=404, detail="file not found")
    target = await ensure_remuxed_async(
        Path(str(row.path)), index, settings.db_path.parent
    )
    if target is None:
        raise HTTPException(status_code=422, detail="无法抽取该音轨")
    return FileResponse(target, media_type="video/x-matroska")
