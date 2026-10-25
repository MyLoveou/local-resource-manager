"""AI 新词候选：拆出词表外的标签，并（可能）归并到词表里的近义标签。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest

import numpy as np
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.application import tag_hint
from app.ai.application.tag_hint import closest_vocabulary_tag, new_tag_candidates
from app.shared.db.migrations import migrate


class ClosestVocabularyTagTests(unittest.TestCase):
    def test_picks_nearest_above_threshold(self) -> None:
        vocabulary = {
            "兽耳": np.asarray([1.0, 0.0], dtype="float32"),
            "风景": np.asarray([0.0, 1.0], dtype="float32"),
        }
        vector = np.asarray([0.99, 0.05], dtype="float32")
        match = closest_vocabulary_tag(vector, vocabulary)
        self.assertIsNotNone(match)
        self.assertEqual(match[0], "兽耳")

    def test_returns_none_when_nothing_is_close(self) -> None:
        vocabulary = {"风景": np.asarray([0.0, 1.0], dtype="float32")}
        vector = np.asarray([1.0, 0.0], dtype="float32")
        self.assertIsNone(closest_vocabulary_tag(vector, vocabulary))


class NewTagCandidateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        tag_hint.invalidate_vocab_vectors()
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = f"{self._tmp.name}/t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def test_only_vocabulary_outsiders_are_returned(self) -> None:
        async with self.factory() as session:
            await session.execute(
                text("INSERT INTO resources (type, title) VALUES ('image', 'r')")
            )
            rid = int(await session.scalar(text("SELECT MAX(id) FROM resources")))
            await session.execute(text("INSERT INTO tags (name) VALUES ('兽耳')"))
            for tag in ("兽耳", "猫耳"):
                await session.execute(
                    text("INSERT INTO ai_tags (resource_id, tag, source) VALUES (:r, :t, 'vlm')"),
                    {"r": rid, "t": tag},
                )
            await session.commit()
            # 没有模型时归并会降级，但「词表外的标签」这条逻辑不受影响
            result = await new_tag_candidates(session, [rid])

        self.assertIn(rid, result)
        names = [item["name"] for item in result[rid]]
        self.assertIn("猫耳", names)
        self.assertNotIn("兽耳", names)
