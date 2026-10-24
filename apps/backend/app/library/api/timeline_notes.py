"""时间线备注 API：日期备注与保存时间线备注。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.library.application.schemas import (
    TimelineNoteList,
    TimelineNoteUpsert,
)
from app.library.application.timeline_notes import TimelineNoteService
from app.library.domain.models import TimelineNote
from app.library.infrastructure.repositories import (
    SavedViewRepository,
    TimelineNoteRepository,
)
from app.shared.db.db import get_session

router = APIRouter(prefix="/timeline-notes", tags=["library-timeline-notes"])


def _service(session: AsyncSession = Depends(get_session)) -> TimelineNoteService:
    return TimelineNoteService(
        TimelineNoteRepository(session),
        SavedViewRepository(session),
    )


@router.get("", response_model=TimelineNoteList)
async def list_date_notes(
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    service: TimelineNoteService = Depends(_service),
) -> TimelineNoteList:
    return TimelineNoteList(items=await service.list_dates(date_from, date_to))


@router.get("/date/{date}", response_model=TimelineNote | None)
async def get_date_note(
    date: str,
    service: TimelineNoteService = Depends(_service),
) -> TimelineNote | None:
    return await service.get_date(date)


@router.put("/date/{date}", response_model=TimelineNote)
async def upsert_date_note(
    date: str,
    body: TimelineNoteUpsert,
    service: TimelineNoteService = Depends(_service),
) -> TimelineNote:
    return await service.upsert_date(date, body.title, body.body, body.location_name)


@router.delete("/date/{date}", status_code=204)
async def delete_date_note(
    date: str,
    service: TimelineNoteService = Depends(_service),
) -> None:
    await service.delete_date(date)


@router.get("/saved-view/{saved_view_id}", response_model=TimelineNote | None)
async def get_saved_view_note(
    saved_view_id: int,
    service: TimelineNoteService = Depends(_service),
) -> TimelineNote | None:
    return await service.get_saved_view(saved_view_id)


@router.put("/saved-view/{saved_view_id}", response_model=TimelineNote)
async def upsert_saved_view_note(
    saved_view_id: int,
    body: TimelineNoteUpsert,
    service: TimelineNoteService = Depends(_service),
) -> TimelineNote:
    return await service.upsert_saved_view(
        saved_view_id, body.title, body.body, body.location_name
    )


@router.delete("/saved-view/{saved_view_id}", status_code=204)
async def delete_saved_view_note(
    saved_view_id: int,
    service: TimelineNoteService = Depends(_service),
) -> None:
    await service.delete_saved_view(saved_view_id)
