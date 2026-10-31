"""时间线备注：日期备注与保存时间线备注。"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.schemas import SavedViewFilters
from app.library.application.timeline_notes import TimelineNoteService
from app.library.infrastructure.repositories import (
    SavedViewRepository,
    TimelineNoteRepository,
)
from app.shared.db.migrations import migrate


class TimelineNoteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path.as_posix()}")

        @event.listens_for(self.engine.sync_engine, "connect")
        def _on_connect(dbapi_conn, _record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def test_date_note_upsert_list_and_delete(self) -> None:
        async with self.factory() as session:
            service = TimelineNoteService(
                TimelineNoteRepository(session), SavedViewRepository(session)
            )
            note = await service.upsert_date(
                "2026-10-18", "C104 Day1", "东京 Big Sight", "东京国际展示场"
            )
            self.assertEqual(note.date, "2026-10-18")
            self.assertEqual(note.location_name, "东京国际展示场")

            listed = await service.list_dates("2026-10-01", "2026-10-31")
            self.assertEqual([item.date for item in listed], ["2026-10-18"])

            updated = await service.upsert_date(
                "2026-10-18", "C104 Day1", "补记", "东京国际展示场"
            )
            self.assertEqual(updated.id, note.id)
            self.assertEqual(updated.body, "补记")

            await service.delete_date("2026-10-18")
            self.assertIsNone(await service.get_date("2026-10-18"))

    async def test_saved_view_note_and_delete_cascade(self) -> None:
        async with self.factory() as session:
            repo = SavedViewRepository(session)
            note_repo = TimelineNoteRepository(session)
            service = TimelineNoteService(note_repo, repo)

            view = await repo.create(
                kind="timeline",
                scope="image",
                name="2026 日本行",
                filters=SavedViewFilters(),
                sort="takenAt",
            )
            assert view.id is not None
            note = await service.upsert_saved_view(
                view.id, "日本行", "一路从东京到大阪", "日本"
            )
            self.assertEqual(note.saved_view_id, view.id)
            self.assertEqual(note.scope, "saved_view")

            await repo.delete(view.id)
            self.assertIsNone(await note_repo.get_saved_view(view.id))

    async def test_empty_note_rejected(self) -> None:
        async with self.factory() as session:
            service = TimelineNoteService(
                TimelineNoteRepository(session), SavedViewRepository(session)
            )
            with self.assertRaises(HTTPException) as ctx:
                await service.upsert_date("2026-10-18", " ", "  ", None)
            self.assertEqual(ctx.exception.status_code, 422)
