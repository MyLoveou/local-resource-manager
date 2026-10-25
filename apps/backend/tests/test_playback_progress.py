"""播放进度与续播（video-management S1）。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.progress import (
    COMPLETE_RATIO,
    MIN_RECORD_SECONDS,
    ProgressService,
    normalize_progress,
)
from app.library.infrastructure.repositories_progress import PlaybackProgressRepository
from app.shared.db.migrations import migrate


class NormalizeProgressTests(unittest.TestCase):
    def test_negative_becomes_zero(self) -> None:
        result = normalize_progress(-5, 100, has_existing=True)
        self.assertEqual(result.position, 0.0)
        self.assertFalse(result.skip)

    def test_short_position_dropped_without_history(self) -> None:
        result = normalize_progress(MIN_RECORD_SECONDS - 1, 100, has_existing=False)
        self.assertTrue(result.skip)

    def test_short_position_kept_when_row_exists(self) -> None:
        result = normalize_progress(2, 100, has_existing=True)
        self.assertFalse(result.skip)
        self.assertEqual(result.position, 2.0)

    def test_reaching_ratio_marks_completed_and_resets(self) -> None:
        result = normalize_progress(96, 100, has_existing=True)
        self.assertTrue(result.completed)
        self.assertEqual(result.position, 0.0)

    def test_ratio_boundary(self) -> None:
        result = normalize_progress(COMPLETE_RATIO * 100, 100, has_existing=True)
        self.assertTrue(result.completed)

    def test_unknown_duration_never_auto_completes(self) -> None:
        result = normalize_progress(5000, None, has_existing=True)
        self.assertFalse(result.completed)


class PlaybackProgressTests(unittest.IsolatedAsyncioTestCase):
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

    async def _seed_resource(self, session, status: str = "active") -> int:
        await session.execute(
            text("INSERT INTO resources (type, title, status) VALUES ('video', 'ep', :status)"),
            {"status": status},
        )
        return int(await session.scalar(text("SELECT MAX(id) FROM resources")))

    async def _seed_file(self, session, resource_id: int, path: str) -> int:
        await session.execute(
            text("INSERT INTO files (resource_id, path, role) VALUES (:rid, :path, 'primary')"),
            {"rid": resource_id, "path": path},
        )
        return int(await session.scalar(text("SELECT MAX(id) FROM files")))

    async def _service(self, session) -> ProgressService:
        return ProgressService(PlaybackProgressRepository(session))

    async def test_record_and_read_back(self) -> None:
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            file_id = await self._seed_file(session, resource_id, "a.mkv")
            service = await self._service(session)
            result = await service.record(resource_id, file_id, 120, 600)
            self.assertEqual(result.status, "saved")
            assert result.progress is not None
            self.assertAlmostEqual(result.progress.position, 120)
            self.assertFalse(result.progress.completed)
            loaded = await service.get(resource_id, file_id)
            assert loaded is not None
            self.assertAlmostEqual(loaded.position, 120)

    async def test_short_position_is_not_written(self) -> None:
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            file_id = await self._seed_file(session, resource_id, "a.mkv")
            service = await self._service(session)
            result = await service.record(resource_id, file_id, 3, 600)
            self.assertEqual(result.status, "skipped")
            self.assertIsNone(await service.get(resource_id, file_id))

    async def test_completed_resets_position(self) -> None:
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            file_id = await self._seed_file(session, resource_id, "a.mkv")
            service = await self._service(session)
            result = await service.record(resource_id, file_id, 590, 600)
            assert result.progress is not None
            self.assertTrue(result.progress.completed)
            self.assertEqual(result.progress.position, 0.0)

    async def test_each_episode_keeps_its_own_position(self) -> None:
        """同一个资源下的两集互不覆盖（进度按 file_id 记）。"""
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            ep1 = await self._seed_file(session, resource_id, "ep1.mkv")
            ep2 = await self._seed_file(session, resource_id, "ep2.mkv")
            service = await self._service(session)
            await service.record(resource_id, ep1, 300, 1400)
            await service.record(resource_id, ep2, 900, 1400)
            one = await service.get(resource_id, ep1)
            two = await service.get(resource_id, ep2)
            assert one is not None and two is not None
            self.assertAlmostEqual(one.position, 300)
            self.assertAlmostEqual(two.position, 900)

    async def test_resume_lists_only_playable(self) -> None:
        async with self.factory() as session:
            active_id = await self._seed_resource(session)
            active_file = await self._seed_file(session, active_id, "a.mkv")
            trashed_id = await self._seed_resource(session, status="trashed")
            trashed_file = await self._seed_file(session, trashed_id, "b.mkv")
            service = await self._service(session)
            await service.record(active_id, active_file, 300, 600)
            self.assertEqual(
                (await service.record(trashed_id, trashed_file, 300, 600)).status,
                "not_found",
            )
            page = await service.resume()
            self.assertEqual([item.file_id for item in page.items], [active_file])
            self.assertEqual(page.total, 1)
            self.assertAlmostEqual(page.items[0].percent, 50.0)

    async def test_completed_item_leaves_resume(self) -> None:
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            file_id = await self._seed_file(session, resource_id, "a.mkv")
            service = await self._service(session)
            await service.record(resource_id, file_id, 599, 600)
            page = await service.resume()
            self.assertEqual(page.items, [])

    async def test_clear_progress(self) -> None:
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            file_id = await self._seed_file(session, resource_id, "a.mkv")
            service = await self._service(session)
            await service.record(resource_id, file_id, 300, 600)
            self.assertEqual(await service.clear(resource_id, file_id), 1)
            self.assertIsNone(await service.get(resource_id, file_id))

    async def test_second_report_returns_fresh_values(self) -> None:
        """同一 session 内二次上报不能读回身份映射里的旧值。

        应用 session 是 expire_on_commit=False，裸 SQL 更新后若不过期，
        随后的 get() 会拿到更新前的实例。
        """
        async with self.factory() as session:
            resource_id = await self._seed_resource(session)
            file_id = await self._seed_file(session, resource_id, "a.mkv")
            service = await self._service(session)
            first = await service.record(resource_id, file_id, 120, 600)
            assert first.progress is not None
            self.assertAlmostEqual(first.progress.position, 120)
            second = await service.record(resource_id, file_id, 590, 600)
            assert second.progress is not None
            self.assertTrue(second.progress.completed)
            self.assertEqual(second.progress.position, 0.0)

    async def test_rejects_file_from_another_resource(self) -> None:
        async with self.factory() as session:
            first = await self._seed_resource(session)
            second = await self._seed_resource(session)
            other_file = await self._seed_file(session, second, "b.mkv")
            service = await self._service(session)
            self.assertEqual(
                (await service.record(first, other_file, 300, 600)).status, "not_found"
            )
