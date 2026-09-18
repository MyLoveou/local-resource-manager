"""库类型平台：注册表、入库、空列表。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.api.imports import validate_import
from app.library.application.import_service import ImportService
from app.library.application.schemas import ImportCreate
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.main import app
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.shared.models import ResourceType, StorageKind

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class LibraryTypePlatformTests(unittest.IsolatedAsyncioTestCase):
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
        self.store = self.root / "library"
        self.ops = FileOps()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    def test_unknown_type_rejected(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/library/imports",
            json={"type": "unknown", "sourceKind": "file", "paths": ["a.mp3"]},
        )
        self.assertIn(response.status_code, (400, 422))

    async def test_audio_import_and_dedupe(self) -> None:
        src = self.root / "a.mp3"
        src.write_bytes(b"ID3fake")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            service = ImportService(repo, store_root=self.store, file_ops=self.ops)
            job = ImportJobState(id="a1")
            await service.run(job, ResourceType.AUDIO, "file", [str(src)])
            self.assertEqual(job.imported, 1)
            items = await repo.list(ResourceType.AUDIO, None, 10, 0, "desc")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].storage_kind, StorageKind.OWNED)
            job2 = ImportJobState(id="a2")
            await service.run(job2, ResourceType.AUDIO, "file", [str(src)])
            self.assertEqual(job2.skipped_duplicate, 1)
            self.assertEqual(await repo.count(ResourceType.AUDIO), 1)

    async def test_game_indexed_default(self) -> None:
        folder = self.root / "MyGame"
        folder.mkdir()
        exe = folder / "MyGame.exe"
        exe.write_bytes(b"MZ")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="g1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.GAME, "directory", [str(folder)]
            )
            self.assertEqual(job.imported, 1)
            items = await repo.list(ResourceType.GAME, None, 10, 0, "desc")
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].storage_kind, StorageKind.INDEXED)
            detail = await repo.get(items[0].id)
            assert detail is not None
            launch = next(f for f in detail.files if f.role == "launch")
            self.assertTrue(Path(launch.path).is_file())
            copied = list((self.store / "game").rglob("*.exe")) if (self.store / "game").exists() else []
            self.assertEqual(copied, [])

    async def test_game_purge_keeps_source(self) -> None:
        folder = self.root / "KeepGame"
        folder.mkdir()
        exe = folder / "KeepGame.exe"
        exe.write_bytes(b"MZ")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="g2")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.GAME, "directory", [str(folder)]
            )
            rid = (await repo.list(ResourceType.GAME, None, 10, 0, "desc"))[0].id
            assert rid is not None
            ok = await LibraryQueryService(
                repo, TaskSummaryRepository(session), file_ops=self.ops, store_root=self.store
            ).purge(rid)
            self.assertTrue(ok)
            self.assertIsNone(await repo.get(rid))
            self.assertTrue(exe.is_file())

    async def test_empty_lists(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            for type_ in (
                ResourceType.AUDIO,
                ResourceType.NOVEL,
                ResourceType.GAME,
                ResourceType.MODEL,
                ResourceType.COMIC,
            ):
                items = await repo.list(type_, None, 10, 0, "desc")
                self.assertEqual(items, [])

    async def test_comic_directory(self) -> None:
        folder = self.root / "book"
        folder.mkdir()
        (folder / "2.png").write_bytes(_PNG)
        (folder / "1.png").write_bytes(_PNG)
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="c1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.COMIC, "directory", [str(folder)]
            )
            self.assertEqual(job.imported, 1)
            items = await repo.list(ResourceType.COMIC, None, 10, 0, "desc")
            self.assertEqual(len(items), 1)
            detail = await repo.get(items[0].id)
            assert detail is not None
            roles = {f.role for f in detail.files if f.role in {"primary", "page", "thumbnail"}}
            self.assertIn("primary", roles)
            self.assertIn("page", roles)

    def test_game_file_source_rejected(self) -> None:
        err = validate_import(
            ImportCreate.model_validate(
                {"type": "game", "sourceKind": "file", "paths": [str(self.root / "a.exe")]}
            )
        )
        self.assertEqual(err, "package import requires a directory")


if __name__ == "__main__":
    unittest.main()
