"""导入复制入库测试。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.api.imports import validate_import
from app.library.application.importers import importer_for
from app.library.application.import_service import ImportService
from app.library.application.packages import ResourcePackage, layout_for
from app.library.application.schemas import ImportCreate
from app.library.infrastructure.import_job_store import ImportJobState, ImportJobStore
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.library.domain.models import ResourceType

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class ImportIngestTests(unittest.IsolatedAsyncioTestCase):
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

    def _png(self, name: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_PNG)
        return path

    async def test_fresh_db_empty(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            self.assertEqual(await repo.count(), 0)

    async def test_copy_keeps_source(self) -> None:
        src = self._png("a.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.IMAGE, "file", [str(src)]
            )
            self.assertEqual(job.imported, 1)
            self.assertTrue(src.is_file())
            self.assertEqual(len(list(self.store.joinpath("image").rglob("primary.png"))), 1)

    async def test_directory_not_a_root(self) -> None:
        folder = self.root / "pics"
        folder.mkdir()
        self._png("pics/a.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.IMAGE, "directory", [str(folder)]
            )
            self.assertEqual(job.imported, 1)

    async def test_duplicate_hash_skipped(self) -> None:
        a = self._png("a.png")
        b = self.root / "b.png"
        b.write_bytes(_PNG)
        async with self.factory() as session:
            repo = ResourceRepository(session)
            service = ImportService(repo, store_root=self.store, file_ops=self.ops)
            job1 = ImportJobState(id="j1")
            await service.run(job1, ResourceType.IMAGE, "file", [str(a)])
            job2 = ImportJobState(id="j2")
            await service.run(job2, ResourceType.IMAGE, "file", [str(b)])
            self.assertEqual(job1.imported, 1)
            self.assertEqual(job2.imported, 0)
            self.assertGreaterEqual(job2.skipped_duplicate, 1)
            self.assertEqual(await repo.count(), 1)

    async def test_image_folder_ignores_txt(self) -> None:
        folder = self.root / "mix"
        folder.mkdir()
        self._png("mix/a.png")
        (folder / "note.txt").write_text("x", encoding="utf-8")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.IMAGE, "directory", [str(folder)]
            )
            self.assertEqual(job.imported, 1)
            self.assertEqual(job.total, 1)

    async def test_cover_falls_back_to_primary(self) -> None:
        src = self._png("a.png")
        pkg = ResourcePackage(
            self.store,
            ResourceType.IMAGE,
            1,
            self.ops,
            cover_falls_back_to_primary=True,
        )
        layout = layout_for(ResourceType.IMAGE)
        assert layout is not None
        roles = layout.place_primary(pkg, src)
        self.assertEqual(pkg.resolve_cover(roles), roles["primary"])
        self.assertFalse(any(p.name.startswith("cover") for p in pkg.root.iterdir()))

    async def test_video_does_not_copy_srt(self) -> None:
        video = self.root / "foo.mp4"
        video.write_bytes(b"not-a-real-mp4")
        (self.root / "foo.srt").write_text("1", encoding="utf-8")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.VIDEO, "file", [str(video)]
            )
            self.assertEqual(job.imported, 1)
        self.assertEqual(list((self.store / "video").rglob("*.srt")), [])
        self.assertTrue(list((self.store / "video").rglob("primary.mp4")))

    def test_validate_missing_file(self) -> None:
        err = validate_import(
            ImportCreate.model_validate(
                {"type": "image", "sourceKind": "file", "paths": [str(self.root / "nope.png")]}
            )
        )
        self.assertEqual(err, "path is not a file")

    async def test_job_store_exclusive(self) -> None:
        store = ImportJobStore()
        first = await store.create_if_idle()
        second = await store.create_if_idle()
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        assert first is not None
        await store.finish(first)
        self.assertIsNotNone(await store.create_if_idle())

    def test_importer_skips_hidden(self) -> None:
        hidden = self.root / ".a.png"
        hidden.write_bytes(_PNG)
        imp = importer_for(ResourceType.IMAGE)
        assert imp is not None
        self.assertFalse(imp.matches(hidden))


if __name__ == "__main__":
    unittest.main()
