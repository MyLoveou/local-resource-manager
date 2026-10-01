"""导入链的同步 IO 必须离开事件循环（D4）。

做法：把目标函数换成会记录「调用发生在哪个线程」的探针。
若调用仍发生在事件循环线程（main thread），说明阻塞 IO 还压在循环上 —— 测试即失败。
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application import import_service as import_service_module
from app.library.application.covers import ingest as cover_ingest_module
from app.library.application.import_service import ImportService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.shared.models import ResourceType

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class ImportConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        db_path = self.root / "t.db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.store = self.root / "library"
        self.ops = FileOps()
        self.event_loop_thread = threading.current_thread()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def _run_import(self, type_: ResourceType, path: Path) -> ImportJobState:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="jc")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, type_, "directory", [str(path)]
            )
            return job

    async def test_comic_page_scan_runs_off_event_loop(self) -> None:
        comic = self.root / "comic"
        comic.mkdir()
        for index in range(3):
            (comic / f"p{index}.png").write_bytes(_PNG)
        seen: dict = {}
        real = import_service_module.comic_pages

        def probe(root: Path):
            seen["thread"] = threading.current_thread()
            return real(root)

        with mock.patch.object(import_service_module, "comic_pages", probe):
            job = await self._run_import(ResourceType.COMIC, comic)

        self.assertEqual(job.imported, 1)
        self.assertIn("thread", seen, "comic_pages 未被调用，测试失去意义")
        self.assertIsNot(
            seen["thread"], self.event_loop_thread, "comic_pages 仍在事件循环线程上执行"
        )

    async def test_game_launch_scan_runs_off_event_loop(self) -> None:
        game = self.root / "g"
        game.mkdir()
        (game / "g.exe").write_bytes(b"MZfake")
        seen: dict = {}
        real = import_service_module.find_launch

        def probe(root: Path):
            seen["thread"] = threading.current_thread()
            return real(root)

        with mock.patch.object(import_service_module, "find_launch", probe):
            job = await self._run_import(ResourceType.GAME, game)

        self.assertEqual(job.imported, 1)
        self.assertIn("thread", seen, "find_launch 未被调用，测试失去意义")
        self.assertIsNot(
            seen["thread"], self.event_loop_thread, "find_launch 仍在事件循环线程上执行"
        )

    async def test_folder_cover_scan_runs_off_event_loop(self) -> None:
        game = self.root / "h"
        game.mkdir()
        (game / "h.exe").write_bytes(b"MZfake")
        seen: dict = {}
        real = cover_ingest_module.find_folder_cover

        def probe(root: Path):
            seen["thread"] = threading.current_thread()
            return real(root)

        with mock.patch.object(cover_ingest_module, "find_folder_cover", probe):
            job = await self._run_import(ResourceType.GAME, game)

        self.assertEqual(job.imported, 1)
        self.assertIn("thread", seen, "find_folder_cover 未被调用，测试失去意义")
        self.assertIsNot(
            seen["thread"], self.event_loop_thread, "find_folder_cover 仍在事件循环线程上执行"
        )


if __name__ == "__main__":
    unittest.main()
