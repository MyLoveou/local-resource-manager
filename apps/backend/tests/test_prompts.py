"""提示词工作台：内置库载荷与存档读写。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.prompts.application.library import library_payload, reset_cache
from app.prompts.infrastructure import repo
from app.shared.db.migrations import migrate


class LibraryTests(unittest.TestCase):
    def test_payload_shape(self) -> None:
        reset_cache()
        payload = library_payload()
        self.assertGreaterEqual(len(payload["categories"]), 20)
        self.assertEqual(len(payload["characters"]), 1401)
        self.assertEqual(len(payload["presets"]), 299)
        self.assertEqual(len(payload["templates"]), 12)
        self.assertIn("anima", payload["models"])
        self.assertIn("moss", payload["models"])
        self.assertGreaterEqual(len(payload["danbooru"]), 1000)
        top = payload["danbooru"][0]
        self.assertIn("count", top)
        self.assertGreater(top["count"], 1000)

    def test_tags_parsed(self) -> None:
        reset_cache()
        payload = library_payload()
        total = sum(len(category["tags"]) for category in payload["categories"])
        self.assertGreater(total, 2000)
        first = payload["categories"][0]["tags"][0]
        self.assertIn("en", first)
        self.assertIn("zh", first)

    def test_presets_have_tags(self) -> None:
        reset_cache()
        payload = library_payload()
        preset = payload["presets"][0]
        self.assertTrue(preset["name"])
        self.assertGreater(len(preset["tags"]), 0)


class SaveRepoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp.name) / "t.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def test_create_list_update_delete(self) -> None:
        async with self.factory() as session:
            save_id = await repo.create_save(
                session,
                {
                    "title": "测试存档",
                    "model": "anima",
                    "positive": "1girl, solo, masterpiece",
                    "negative": "lowres",
                    "params": {"steps": 10},
                },
                ["1girl", "solo"],
            )
            self.assertGreater(save_id, 0)

            items = await repo.list_saves(session)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["params"]["steps"], 10)

            by_tag = await repo.list_saves(session, tag="solo")
            self.assertEqual(len(by_tag), 1)

            ok = await repo.update_save(
                session, save_id, {"title": "改名", "favorite": True}, None
            )
            self.assertTrue(ok)
            row = await repo.get_save(session, save_id)
            self.assertEqual(row["title"], "改名")
            self.assertTrue(row["favorite"])

            favs = await repo.list_saves(session, favorite=True)
            self.assertEqual(len(favs), 1)

            self.assertTrue(await repo.delete_save(session, save_id))
            self.assertIsNone(await repo.get_save(session, save_id))

    async def test_history_trim_keeps_pinned(self) -> None:
        async with self.factory() as session:
            first = await repo.add_history(
                session, model="anima", positive="a", negative="", save_id=None
            )
            await repo.pin_history(session, first, True)
            for index in range(45):
                await repo.add_history(
                    session, model="anima", positive=f"p{index}", negative="", save_id=None
                )
            items = await repo.list_history(session, limit=100)
            self.assertLessEqual(len(items), 41)
            self.assertTrue(any(item["pinned"] for item in items))

    async def test_custom_and_settings(self) -> None:
        async with self.factory() as session:
            tag_id = await repo.add_custom(
                session, "prompt_custom_tags", {"en": "my tag", "zh": "我的标签", "category": "其他"}
            )
            self.assertGreater(tag_id, 0)
            tags = await repo.list_custom(session, "prompt_custom_tags")
            self.assertEqual(tags[0]["en"], "my tag")

            await repo.put_settings(session, {"defaultModel": "moss", "showNsfw": False})
            settings = await repo.get_settings(session)
            self.assertEqual(settings["defaultModel"], "moss")
            self.assertFalse(settings["showNsfw"])
    async def test_save_keeps_preview_image(self) -> None:
        async with self.factory() as session:
            save_id = await repo.create_save(
                session,
                {
                    "title": "带图",
                    "model": "anima",
                    "positive": "1girl",
                    "negative": "",
                    "image_data": "data:image/jpeg;base64,AAAA",
                },
                [],
            )
            row = await repo.get_save(session, save_id)
            self.assertEqual(row["image_data"], "data:image/jpeg;base64,AAAA")

            await repo.update_save(session, save_id, {"image_data": "data:image/jpeg;base64,BBBB"}, None)
            row = await repo.get_save(session, save_id)
            self.assertEqual(row["image_data"], "data:image/jpeg;base64,BBBB")