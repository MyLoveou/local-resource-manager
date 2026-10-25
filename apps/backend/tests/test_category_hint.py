"""分类建议（闭集）：用同标签资源的分类投票，只从已有分类里选。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.application.category_hint import category_hints
from app.shared.db.migrations import migrate


class CategoryHintTests(unittest.IsolatedAsyncioTestCase):
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

    async def _tag(self, session, name: str) -> int:
        await session.execute(text("INSERT INTO tags (name) VALUES (:n)"), {"n": name})
        return int(await session.scalar(text("SELECT MAX(id) FROM tags")))

    async def _category(self, session, name: str) -> int:
        await session.execute(
            text("INSERT INTO categories (name, type) VALUES (:n, 'image')"), {"n": name}
        )
        return int(await session.scalar(text("SELECT MAX(id) FROM categories")))

    async def test_suggests_category_voted_by_tag_neighbours(self) -> None:
        async with self.factory() as session:
            tag = await self._tag(session, "漫展")
            cat = await self._category(session, "漫展返图")
            first = await self._resource(session, "a")
            second = await self._resource(session, "b")
            target = await self._resource(session, "target")
            for rid in (first, second, target):
                await session.execute(
                    text("INSERT INTO resource_tags (resource_id, tag_id) VALUES (:r, :t)"),
                    {"r": rid, "t": tag},
                )
            for rid in (first, second):
                await session.execute(
                    text(
                        "INSERT INTO resource_categories (resource_id, category_id) "
                        "VALUES (:r, :c)"
                    ),
                    {"r": rid, "c": cat},
                )
            await session.commit()

            hints = await category_hints(session, [target])

        self.assertIn(target, hints)
        self.assertEqual(hints[target][0]["name"], "漫展返图")
        self.assertEqual(hints[target][0]["confidence"], 1.0)

    async def test_single_vote_is_not_enough(self) -> None:
        async with self.factory() as session:
            tag = await self._tag(session, "夜景")
            cat = await self._category(session, "夜拍")
            only = await self._resource(session, "a")
            target = await self._resource(session, "target")
            for rid in (only, target):
                await session.execute(
                    text("INSERT INTO resource_tags (resource_id, tag_id) VALUES (:r, :t)"),
                    {"r": rid, "t": tag},
                )
            await session.execute(
                text(
                    "INSERT INTO resource_categories (resource_id, category_id) "
                    "VALUES (:r, :c)"
                ),
                {"r": only, "c": cat},
            )
            await session.commit()
            hints = await category_hints(session, [target])

        self.assertNotIn(target, hints)

    async def test_already_assigned_category_is_not_repeated(self) -> None:
        async with self.factory() as session:
            tag = await self._tag(session, "漫展")
            cat = await self._category(session, "漫展返图")
            first = await self._resource(session, "a")
            second = await self._resource(session, "b")
            target = await self._resource(session, "target")
            for rid in (first, second, target):
                await session.execute(
                    text("INSERT INTO resource_tags (resource_id, tag_id) VALUES (:r, :t)"),
                    {"r": rid, "t": tag},
                )
            for rid in (first, second, target):
                await session.execute(
                    text(
                        "INSERT INTO resource_categories (resource_id, category_id) "
                        "VALUES (:r, :c)"
                    ),
                    {"r": rid, "c": cat},
                )
            await session.commit()
            hints = await category_hints(session, [target])

        self.assertNotIn(target, hints)
