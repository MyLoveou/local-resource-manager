"""统一任务表：落库、去重、中断恢复、清理。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.shared import tasks
from app.shared.db.migrations import migrate


class TasksTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.db_path = root / "t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path.as_posix()}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def test_create_and_finish(self) -> None:
        async with self.factory() as session:
            task_id = await tasks.create(
                session, kind=tasks.KIND_SCRAPE, title="刮削", total=10
            )
            self.assertIsNotNone(task_id)
            await tasks.start(session, task_id)
            await tasks.progress(session, task_id, done=5, percent=50)
            await tasks.finish(session, task_id)
            rows = await tasks.list_tasks(session)
            row = rows[0]
            self.assertEqual(row["state"], tasks.DONE)
            self.assertEqual(row["percent"], 100)
            self.assertEqual(row["attempts"], 1)

    async def test_active_duplicate_is_rejected(self) -> None:
        async with self.factory() as session:
            first = await tasks.create(
                session, kind=tasks.KIND_SCRAPE, title="a", dedupe_key="scrape:1:x"
            )
            second = await tasks.create(
                session, kind=tasks.KIND_SCRAPE, title="b", dedupe_key="scrape:1:x"
            )
            self.assertIsNotNone(first)
            self.assertIsNone(second)

    async def test_finished_task_allows_new_one(self) -> None:
        async with self.factory() as session:
            first = await tasks.create(
                session, kind=tasks.KIND_SCRAPE, title="a", dedupe_key="scrape:1:x"
            )
            await tasks.start(session, first)
            await tasks.finish(session, first)
            second = await tasks.create(
                session, kind=tasks.KIND_SCRAPE, title="b", dedupe_key="scrape:1:x"
            )
            self.assertIsNotNone(second)

    async def test_recover_marks_running_interrupted_and_requeues_scrape(self) -> None:
        async with self.factory() as session:
            scrape = await tasks.create(session, kind=tasks.KIND_SCRAPE, title="s")
            await tasks.start(session, scrape)
            imp = await tasks.create(session, kind=tasks.KIND_IMPORT, title="i")
            await tasks.start(session, imp)

            result = await tasks.recover_on_startup(session)
            self.assertEqual(result["interrupted"], 2)

            rows = {row["kind"]: row for row in await tasks.list_tasks(session)}
            self.assertEqual(rows[tasks.KIND_SCRAPE]["state"], tasks.QUEUED)
            # 导入不自动续跑，等用户点继续
            self.assertEqual(rows[tasks.KIND_IMPORT]["state"], tasks.INTERRUPTED)

    async def test_fail_records_reason(self) -> None:
        async with self.factory() as session:
            task_id = await tasks.create(session, kind=tasks.KIND_IMPORT, title="i")
            await tasks.start(session, task_id)
            await tasks.fail(session, task_id, "搜索超时")
            row = (await tasks.list_tasks(session))[0]
            self.assertEqual(row["state"], tasks.FAILED)
            self.assertIn("超时", row["error"])

    async def test_prune_removes_old_terminal_only(self) -> None:
        async with self.factory() as session:
            old = await tasks.create(session, kind=tasks.KIND_IMPORT, title="old")
            await tasks.start(session, old)
            await tasks.finish(session, old)
            await session.execute(
                tasks.text("UPDATE tasks SET finished_at = '2000-01-01 00:00:00'")
            )
            await session.commit()
            alive = await tasks.create(session, kind=tasks.KIND_SCRAPE, title="alive")
            await tasks.start(session, alive)

            removed = await tasks.prune(session, days=7)
            self.assertEqual(removed, 1)
            rows = await tasks.list_tasks(session)
            self.assertEqual([row["id"] for row in rows], [alive])
