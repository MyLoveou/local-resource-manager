"""智能导入：特典命名的空格/中文标记，以及 AI 开关的默认关闭行为。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.smart_import.base import ActionContext, Suggestion
from app.library.application.smart_import.preferences import (
    DEFAULT_ENABLED,
    is_ai_enabled,
    set_ai_enabled,
)
from app.library.application.smart_import.title_ai import refine_suggestions
from app.library.application.smart_import.title_clean import clean_release_name
from app.library.domain.models import ResourceType
from app.shared.db.migrations import migrate

PV = "[DBD-Raws][Isekai Ojisan][PV][08][1080P][BDRip][HEVC-10bit][FLAC]"
TOKUTEN = "[DBD-Raws][Isekai Ojisan][Tokuten][01][1080P][BDRip][HEVC-10bit][FLAC]"


class ExtraTitleTests(unittest.TestCase):
    def test_pv_keeps_spacing(self) -> None:
        self.assertEqual(clean_release_name(PV).title, "Isekai Ojisan PV 08")

    def test_tokuten_is_written_in_chinese(self) -> None:
        self.assertEqual(clean_release_name(TOKUTEN).title, "Isekai Ojisan 特典 01")

    def test_work_title_drops_extra_marker(self) -> None:
        self.assertEqual(clean_release_name(PV, keep_episode=False).title, "Isekai Ojisan")

    def test_cjk_boundary_has_no_space(self) -> None:
        result = clean_release_name("[DBD-Raws][异世界舅舅][PV][08][1080P]")
        self.assertEqual(result.title, "异世界舅舅 PV 08")


class _DbCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "t.db"
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")

        @event.listens_for(self.engine.sync_engine, "connect")
        def _on_connect(dbapi_conn, _record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()


class AiToggleTests(_DbCase):
    async def test_default_is_enabled(self) -> None:
        async with self.factory() as session:
            self.assertTrue(DEFAULT_ENABLED)
            self.assertTrue(await is_ai_enabled(session))

    async def test_roundtrip(self) -> None:
        async with self.factory() as session:
            await set_ai_enabled(session, True)
            self.assertTrue(await is_ai_enabled(session))
            await set_ai_enabled(session, False)
            self.assertFalse(await is_ai_enabled(session))

    async def test_refine_is_skipped_when_disabled(self) -> None:
        calls: list[str] = []

        async def fake(prompt: str) -> str | None:
            calls.append(prompt)
            return '{"keep": [1]}'

        ctx = ActionContext(resource_id=1, type=ResourceType.ANIME, file_stem="x", dir_name=PV)
        suggestion = Suggestion(
            field="title", value={"text": "Isekai Ojisan1080P"}, confidence=0.55, reason="可疑"
        )
        out = await refine_suggestions(ctx, [suggestion], complete=fake, enabled=False)
        self.assertEqual(out[0], suggestion)
        self.assertEqual(calls, [])

    async def test_ai_only_when_rules_found_nothing(self) -> None:
        from app.library.application.smart_import.title_ai import ai_only_suggestion

        async def fake(prompt: str) -> str | None:
            return '{"keep": [1]}'

        ctx = ActionContext(resource_id=1, type=ResourceType.ANIME, file_stem="x", dir_name=PV)
        suggestion = await ai_only_suggestion(ctx, complete=fake)
        self.assertIsNotNone(suggestion)
        assert suggestion is not None
        self.assertEqual(suggestion.source, "ai")
        self.assertEqual(suggestion.value, {"text": "Isekai Ojisan"})

    async def test_refine_runs_when_enabled(self) -> None:
        async def fake(prompt: str) -> str | None:
            return '{"keep": [1]}'

        ctx = ActionContext(resource_id=1, type=ResourceType.ANIME, file_stem="x", dir_name=PV)
        suggestion = Suggestion(
            field="title", value={"text": "Isekai Ojisan1080P"}, confidence=0.55, reason="可疑"
        )
        out = await refine_suggestions(ctx, [suggestion], complete=fake, enabled=True)
        self.assertEqual(out[0].source, "ai")
        self.assertEqual(out[0].value, {"text": "Isekai Ojisan"})
