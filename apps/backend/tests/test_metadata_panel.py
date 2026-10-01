"""元数据面板：详情、PATCH 词条、换封面。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.schemas import CoverReplace, ResourcePatch
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.library.domain.models import ResourceType

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class MetadataPanelTests(unittest.IsolatedAsyncioTestCase):
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

    async def _import_one(self, session) -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id="j1")
        await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
            job, ResourceType.IMAGE, "file", [str(self._png("a.png"))]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    def _svc(self, session) -> LibraryQueryService:
        return LibraryQueryService(
            ResourceRepository(session),
            TaskSummaryRepository(session),
            file_ops=self.ops,
            store_root=self.store,
        )

    async def test_detail_has_files_and_vocab(self) -> None:
        async with self.factory() as session:
            rid = await self._import_one(session)
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            self.assertTrue(got.created_at)
            self.assertEqual(got.tags, [])
            self.assertIsNone(got.category)
            primaries = [f for f in got.files if f.role == "primary"]
            self.assertEqual(len(primaries), 1)
            self.assertGreater(primaries[0].size or 0, 0)

    async def test_get_missing(self) -> None:
        async with self.factory() as session:
            self.assertIsNone(await ResourceRepository(session).get(99999))

    async def test_patch_rating_only(self) -> None:
        async with self.factory() as session:
            rid = await self._import_one(session)
            repo = ResourceRepository(session)
            before = await repo.get(rid)
            assert before is not None
            title = before.title
            updated = await self._svc(session).patch(rid, ResourcePatch(rating=8))
            assert updated is not None
            self.assertEqual(updated.rating, 8)
            self.assertEqual(updated.title, title)

    async def test_patch_tag_names(self) -> None:
        async with self.factory() as session:
            rid = await self._import_one(session)
            svc = self._svc(session)
            updated = await svc.patch(rid, ResourcePatch(tag_names=["夜景", "风景"]))
            assert updated is not None
            self.assertEqual(sorted(t.name for t in updated.tags), ["夜景", "风景"])
            tags = await ResourceRepository(session).list_tags()
            self.assertEqual(sorted(t.name for t in tags), ["夜景", "风景"])
            cleared = await svc.patch(rid, ResourcePatch(tag_names=[]))
            assert cleared is not None
            self.assertEqual(cleared.tags, [])

    async def test_patch_creates_category(self) -> None:
        async with self.factory() as session:
            rid = await self._import_one(session)
            updated = await self._svc(session).patch(rid, ResourcePatch(category_name="风景"))
            assert updated is not None
            assert updated.category is not None
            self.assertEqual(updated.category.name, "风景")
            cats = await ResourceRepository(session).list_categories()
            self.assertEqual([c.name for c in cats], ["风景"])

    async def test_replace_cover_keeps_primary(self) -> None:
        src = self.root / "a.mp3"
        src.write_bytes(b"ID3")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.AUDIO, "file", [str(src)]
            )
            rid = (await repo.list(ResourceType.AUDIO, None, 10, 0, "desc"))[0].id
            before = await repo.get(rid)
            assert before is not None
            primary = next(f for f in before.files if f.role == "primary")
            cover_src = self._png("cover.png")
            after = await self._svc(session).replace_cover(rid, CoverReplace(path=str(cover_src)))
            assert after is not None
            covers = [f for f in after.files if f.role == "cover"]
            self.assertEqual(len(covers), 1)
            new_primary = next(f for f in after.files if f.role == "primary")
            self.assertEqual(new_primary.sha256, primary.sha256)
            self.assertEqual(new_primary.path, primary.path)
            self.assertIn("/files/", after.cover_path or "")

    async def test_replace_cover_invalid(self) -> None:
        src = self.root / "a.mp3"
        src.write_bytes(b"ID3")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.AUDIO, "file", [str(src)]
            )
            rid = (await repo.list(ResourceType.AUDIO, None, 10, 0, "desc"))[0].id
            before = await repo.get(rid)
            assert before is not None
            with self.assertRaises(ValueError):
                await self._svc(session).replace_cover(
                    rid, CoverReplace(path=str(self.root / "missing.png"))
                )
            after = await repo.get(rid)
            assert after is not None
            self.assertEqual(after.cover_path, before.cover_path)
            self.assertFalse(any(f.role == "cover" for f in after.files))
