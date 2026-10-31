"""分类建议的向量兜底：标签没命中时用 CLIP 近邻投票。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.application.category_hint import suggest_categories
from app.ai.infrastructure.model_store import MODEL_ID
from app.shared.db.migrations import migrate


class VectorCategoryHintTests(unittest.IsolatedAsyncioTestCase):
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

    async def _resource(self, session, name: str) -> int:
        await session.execute(
            text("INSERT INTO resources (type, title) VALUES ('image', :t)"), {"t": name}
        )
        return int(await session.scalar(text("SELECT MAX(id) FROM resources")))

    async def _category(self, session, name: str) -> int:
        await session.execute(
            text("INSERT INTO categories (name, type) VALUES (:n, 'image')"), {"n": name}
        )
        return int(await session.scalar(text("SELECT MAX(id) FROM categories")))

    async def _vector(self, session, rid: int, values: list[float]) -> None:
        await session.execute(
            text(
                "INSERT INTO ai_vectors (resource_id, model_id, dim, vector) "
                "VALUES (:r, :m, :d, :v)"
            ),
            {
                "r": rid,
                "m": MODEL_ID,
                "d": len(values),
                "v": np.asarray(values, dtype="float32").tobytes(),
            },
        )

    async def _link(self, session, rid: int, cat: int) -> None:
        await session.execute(
            text(
                "INSERT INTO resource_categories (resource_id, category_id) "
                "VALUES (:r, :c)"
            ),
            {"r": rid, "c": cat},
        )

    async def test_vector_fallback_when_tags_do_not_match(self) -> None:
        async with self.factory() as session:
            cat = await self._category(session, "街拍")
            target = await self._resource(session, "target")
            first = await self._resource(session, "n1")
            second = await self._resource(session, "n2")
            await self._vector(session, target, [1.0, 0.0, 0.0, 0.0])
            await self._vector(session, first, [0.99, 0.1, 0.0, 0.0])
            await self._vector(session, second, [0.95, 0.2, 0.0, 0.0])
            await self._link(session, first, cat)
            await self._link(session, second, cat)
            await session.commit()

            hints = await suggest_categories(session, [target])

        self.assertIn(target, hints)
        self.assertEqual(hints[target][0]["name"], "街拍")
        self.assertGreater(hints[target][0]["confidence"], 0.9)

    async def test_far_neighbours_are_ignored(self) -> None:
        async with self.factory() as session:
            cat = await self._category(session, "街拍")
            target = await self._resource(session, "target")
            far = await self._resource(session, "far")
            await self._vector(session, target, [1.0, 0.0, 0.0, 0.0])
            await self._vector(session, far, [0.0, 1.0, 0.0, 0.0])
            await self._link(session, far, cat)
            await session.commit()
            hints = await suggest_categories(session, [target])

        self.assertNotIn(target, hints)
