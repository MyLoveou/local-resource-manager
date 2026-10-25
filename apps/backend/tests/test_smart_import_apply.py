"""智能导入：建议落库、分组、采纳与忽略（S1）。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.smart_import.pipeline import group_pending, suggest_after_ingest
from app.library.domain.models import ResourceType
from app.library.infrastructure.repositories import ResourceRepository
from app.library.infrastructure.repositories_suggestions import SuggestionRepository
from app.shared.db.migrations import migrate


class SmartImportApplyTests(unittest.IsolatedAsyncioTestCase):
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

    async def _seed(self, session, title: str = "原名") -> int:
        await session.execute(
            text("INSERT INTO resources (type, title) VALUES ('video', :t)"), {"t": title}
        )
        return int(await session.scalar(text("SELECT MAX(id) FROM resources")))

    async def _suggest(self, session, resource_id: int, source_name: str, job_id: str = "j1") -> int:
        repo = ResourceRepository(session)
        return await suggest_after_ingest(
            repo,
            job_id=job_id,
            resource_id=resource_id,
            type_=ResourceType.VIDEO,
            source_name=source_name,
        )

    async def test_writes_source_name_and_suggestion(self) -> None:
        async with self.factory() as session:
            rid = await self._seed(session)
            written = await self._suggest(
                session, rid, "[VCB-Studio] Frieren [01][1080p].mkv"
            )
            self.assertEqual(written, 1)
            name = await session.scalar(
                text("SELECT source_name FROM resources WHERE id = :id"), {"id": rid}
            )
            self.assertEqual(name, "[VCB-Studio] Frieren [01][1080p].mkv")

    async def test_clean_name_produces_nothing(self) -> None:
        async with self.factory() as session:
            rid = await self._seed(session)
            self.assertEqual(await self._suggest(session, rid, "夏日海边.mkv"), 0)
            name = await session.scalar(
                text("SELECT source_name FROM resources WHERE id = :id"), {"id": rid}
            )
            self.assertEqual(name, "夏日海边.mkv")

    async def test_same_value_groups_together(self) -> None:
        async with self.factory() as session:
            first = await self._seed(session)
            second = await self._seed(session)
            await self._suggest(session, first, "[VCB-Studio] Frieren [01][1080p].mkv")
            await self._suggest(session, second, "[VCB-Studio] Frieren [02][1080p].mkv")
            rows = await SuggestionRepository(session).list_pending("j1")
            groups = group_pending(rows)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["count"], 2)
            self.assertEqual(groups[0]["value"]["text"], "Frieren")

    async def test_group_confidence_is_minimum(self) -> None:
        async with self.factory() as session:
            strong = await self._seed(session)
            weak = await self._seed(session)
            await self._suggest(session, strong, "[VCB-Studio] Frieren [01][1080p].mkv")
            await self._suggest(session, weak, "[VCB-Studio] Frieren 01.mkv")
            rows = await SuggestionRepository(session).list_pending("j1")
            groups = group_pending(rows)
            self.assertEqual(len(groups), 1)
            self.assertLessEqual(groups[0]["confidence"], 0.95)

    async def test_apply_updates_title_and_marks_accepted(self) -> None:
        async with self.factory() as session:
            rid = await self._seed(session)
            await self._suggest(session, rid, "[VCB-Studio] Frieren [01][1080p].mkv")
            repo = SuggestionRepository(session)
            result = await repo.apply(groups=[("title", {"text": "Frieren"})])
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(result["updated_resources"], 1)
            title = await session.scalar(
                text("SELECT title FROM resources WHERE id = :id"), {"id": rid}
            )
            self.assertEqual(title, "Frieren")
            status = await session.scalar(
                text("SELECT status FROM import_suggestions WHERE resource_id = :id"),
                {"id": rid},
            )
            self.assertEqual(status, "accepted")

    async def test_apply_respects_min_confidence(self) -> None:
        async with self.factory() as session:
            rid = await self._seed(session)
            # 只有集号可剥，置信度落在中间档
            await self._suggest(session, rid, "夏日海边 01.mkv")
            repo = SuggestionRepository(session)
            result = await repo.apply(groups=[("title", {"text": "夏日海边"})], min_confidence=0.9)
            self.assertEqual(result["accepted"], 0)

    async def test_reject_all(self) -> None:
        async with self.factory() as session:
            rid = await self._seed(session)
            await self._suggest(session, rid, "[VCB-Studio] Frieren [01][1080p].mkv")
            repo = SuggestionRepository(session)
            result = await repo.reject(reject_all=True)
            self.assertEqual(result["rejected"], 1)
            self.assertEqual(await repo.list_pending("j1"), [])
            title = await session.scalar(
                text("SELECT title FROM resources WHERE id = :id"), {"id": rid}
            )
            self.assertEqual(title, "原名")

    async def test_summary_counts(self) -> None:
        async with self.factory() as session:
            strong = await self._seed(session)
            weak = await self._seed(session)
            await self._suggest(session, strong, "[VCB-Studio] Frieren [01][1080p].mkv")
            await self._suggest(session, weak, "夏日海边 01.mkv")
            summary = await SuggestionRepository(session).summary()
            self.assertEqual(summary["pending"], 2)
            self.assertEqual(summary["highConfidence"], 1)

    async def test_directory_name_wins_when_confident(self) -> None:
        async with self.factory() as session:
            rid = await self._seed(session)
            repo = ResourceRepository(session)
            await suggest_after_ingest(
                repo,
                job_id="j1",
                resource_id=rid,
                type_=ResourceType.ANIME,
                source_name="[VCB-Studio] Frieren [1080p]",
                dir_name="[VCB-Studio] Frieren [Ma10p_1080p]",
            )
            rows = await SuggestionRepository(session).list_pending("j1")
            groups = group_pending(rows)
            self.assertEqual(groups[0]["value"]["text"], "Frieren")
