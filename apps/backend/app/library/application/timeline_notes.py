"""时间线备注：全局日期备注与保存时间线备注。"""
from datetime import datetime

from fastapi import HTTPException

from app.library.domain.models import TimelineNote
from app.library.infrastructure.repositories import (
    SavedViewRepository,
    TimelineNoteRepository,
)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_date(value: str) -> str:
    raw = value.strip()
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="date must be YYYY-MM-DD") from exc
    return parsed.strftime("%Y-%m-%d")


class TimelineNoteService:
    def __init__(self, notes: TimelineNoteRepository, saved_views: SavedViewRepository):
        self._notes = notes
        self._saved_views = saved_views

    async def get_date(self, date: str) -> TimelineNote | None:
        return await self._notes.get_date(_clean_date(date))

    async def list_dates(
        self, date_from: str | None = None, date_to: str | None = None
    ) -> list[TimelineNote]:
        start = _clean_date(date_from) if date_from else None
        end = _clean_date(date_to) if date_to else None
        return await self._notes.list_dates(start, end)

    async def get_saved_view(self, saved_view_id: int) -> TimelineNote | None:
        if await self._saved_views.get(saved_view_id) is None:
            raise HTTPException(status_code=404, detail="saved view not found")
        return await self._notes.get_saved_view(saved_view_id)

    async def upsert_date(
        self, date: str, title: str, body: str | None, location_name: str | None
    ) -> TimelineNote:
        cleaned_date = _clean_date(date)
        return await self._upsert(
            cleaned_date,
            title,
            body,
            location_name,
            saved_view_id=None,
        )

    async def upsert_saved_view(
        self,
        saved_view_id: int,
        title: str,
        body: str | None,
        location_name: str | None,
    ) -> TimelineNote:
        if await self._saved_views.get(saved_view_id) is None:
            raise HTTPException(status_code=404, detail="saved view not found")
        return await self._upsert(
            None,
            title,
            body,
            location_name,
            saved_view_id=saved_view_id,
        )

    async def _upsert(
        self,
        date: str | None,
        title: str,
        body: str | None,
        location_name: str | None,
        *,
        saved_view_id: int | None,
    ) -> TimelineNote:
        cleaned_title = title.strip()
        cleaned_body = _clean_optional(body)
        cleaned_location = _clean_optional(location_name)
        if not cleaned_title and not cleaned_body and not cleaned_location:
            raise HTTPException(status_code=422, detail="note is empty")
        if date is not None:
            return await self._notes.upsert_date(
                date, cleaned_title, cleaned_body, cleaned_location
            )
        assert saved_view_id is not None
        return await self._notes.upsert_saved_view(
            saved_view_id, cleaned_title, cleaned_body, cleaned_location
        )

    async def delete_date(self, date: str) -> None:
        deleted = await self._notes.delete_date(_clean_date(date))
        if not deleted:
            raise HTTPException(status_code=404, detail="note not found")

    async def delete_saved_view(self, saved_view_id: int) -> None:
        if await self._saved_views.get(saved_view_id) is None:
            raise HTTPException(status_code=404, detail="saved view not found")
        deleted = await self._notes.delete_saved_view(saved_view_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="note not found")
