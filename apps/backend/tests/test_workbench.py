"""工作目录、消费记录、消费渠道。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.use_cases import LibraryQueryService
from app.library.application.workbench import add_work_directory, add_work_note, record_consumption
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.settings.application.schemas import ChannelSetting, ConsumeSettingsPatch
from app.settings.application.service import get_view, patch_consume
from app.shared.db.migrations import migrate
from app.shared.db.orm import ResourceRow


class WorkbenchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.db_path = self.root / "t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path.as_posix()}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    def _svc(self, session) -> LibraryQueryService:
        return LibraryQueryService(ResourceRepository(session), TaskSummaryRepository(session))

    async def test_work_directory_todo_note_and_consumption_survive_restart(self) -> None:
        folder = self.root / "proj"
        folder.mkdir()
        async with self.factory() as session:
            created = await add_work_directory(session, str(folder))
            self.assertIsNotNone(created.id)
            rid = created.id
            assert rid is not None
            self.assertEqual(created.type.value, "work_directory")
            self.assertEqual(created.storage_kind.value, "indexed")
            await ResourceRepository(session).add_todo(rid, "写方案")
            noted = await add_work_note(session, rid, "备", "记一下")
            assert noted is not None
            self.assertEqual(noted.extra["workNotes"][0]["content"], "记一下")

        async with self.factory() as session:
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            self.assertEqual(got.todos[0].content, "写方案")
            self.assertEqual(got.extra["workNotes"][0]["title"], "备")
            await record_consumption(session, rid, "workbench")
            overview = await self._svc(session).overview()
            self.assertTrue(any(item.id == rid for item in overview.active_work))
            self.assertEqual(overview.recent_consumption[0].resource_id, rid)
            self.assertEqual(overview.recent_consumption[0].action, "workbench")

        async with self.factory() as session:
            with self.assertRaises(ValueError):
                await add_work_directory(session, str(folder))
            with self.assertRaises(ValueError):
                await add_work_directory(session, str(self.root / "missing"))

    async def test_consume_channels_roundtrip_and_workbench_only(self) -> None:
        async with self.factory() as session:
            view = await patch_consume(
                session,
                ConsumeSettingsPatch(
                    channels={
                        "video": ChannelSetting(mode="command", command="mpv {path}"),
                        "work_directory": ChannelSetting(mode="embedded", command="x"),
                    }
                ),
                self.db_path,
                "0.0.0",
            )
            self.assertEqual(view.consume.channels["video"].mode, "command")
            self.assertEqual(view.consume.channels["video"].command, "mpv {path}")
            self.assertEqual(view.consume.channels["work_directory"].mode, "workbench")
            self.assertEqual(view.consume.channels["image"].mode, "embedded")
            self.assertEqual(view.consume.channels["novel"].mode, "system")
        async with self.factory() as session:
            again = await get_view(session, self.db_path, "0.0.0")
            self.assertEqual(again.consume.channels["video"].command, "mpv {path}")

    async def test_trashed_directory_is_restored_on_add(self) -> None:
        folder = self.root / "again"
        folder.mkdir()
        async with self.factory() as session:
            created = await add_work_directory(session, str(folder))
            rid = created.id
            assert rid is not None
            repo = ResourceRepository(session)
            row = await repo.get(rid)
            assert row is not None
            row.to_trash()
            await repo.update(rid, row)
            restored = await add_work_directory(session, str(folder))
            self.assertEqual(restored.id, rid)
            self.assertEqual(restored.status.value, "active")

    async def test_recent_open_stays_on_home_after_metadata_goes_stale(self) -> None:
        folder = self.root / "stale"
        folder.mkdir()
        async with self.factory() as session:
            created = await add_work_directory(session, str(folder))
            rid = created.id
            assert rid is not None
            stored = await session.get(ResourceRow, rid)
            assert stored is not None
            stored.updated_at = "2000-01-01 00:00:00"
            await session.commit()
            await record_consumption(session, rid, "workbench")
            overview = await self._svc(session).overview()
            self.assertTrue(any(item.id == rid for item in overview.active_work))
