"""批量打标 + 合集导出：算法、用例、端点。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.library.application.export_naming import export_name, safe_title
from app.library.application.import_service import ImportService
from app.library.application.packages.resource_package import ResourcePackage
from app.library.application.schemas import ResourceBatchRequest, ResourceSortField
from app.library.application.use_cases import CollectionService, LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import (
    CollectionRepository,
    ResourceRepository,
    TaskSummaryRepository,
)
from app.shared.config import settings
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.library.domain.models import ResourceStatus, ResourceType

from app.main import app

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


def _png_with_seed(seed: int) -> bytes:
    """同一张 1x1 PNG 改最后一个像素字节并重压 IDAT，生成内容唯一的合法 PNG（避免查重撞哈希）。"""
    import struct
    import zlib

    rest = _PNG[8:]
    pos = 0
    out = bytearray(_PNG[:8])
    while pos < len(rest):
        length = struct.unpack(">I", rest[pos : pos + 4])[0]
        kind = rest[pos + 4 : pos + 8]
        data = rest[pos + 8 : pos + 8 + length]
        if kind == b"IDAT":
            raw = zlib.decompress(data)
            raw = raw[:-1] + bytes([raw[-1] ^ (seed & 0xFF)])
            data = zlib.compress(raw)
        out += struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        pos += 12 + length
    return bytes(out)


class ExportNamingTests(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(export_name(1, "标题", ".jpg"), "001_标题.jpg")

    def test_invalid_chars_replaced(self) -> None:
        self.assertEqual(export_name(12, 'a/b\\c:d*e?f"g<h>i|j', ".png"), "012_a_b_c_d_e_f_g_h_i_j.png")

    def test_empty_title_fallback(self) -> None:
        self.assertEqual(export_name(3, "  ", ".jpg"), "003_untitled.jpg")

    def test_long_title_truncated(self) -> None:
        self.assertEqual(len(safe_title("长" * 200)), 80)

    def test_ext_without_dot(self) -> None:
        self.assertEqual(export_name(7, "x", "jpg"), "007_x.jpg")


class BatchTagExportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.db_path = self.root / "t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path.as_posix()}")

        @event.listens_for(self.engine.sync_engine, "connect")
        def _on_connect(dbapi_conn, _record) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.store = self.root / "library"
        self.ops = FileOps()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    def _png(self, name: str, seed: int = 0) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_png_with_seed(seed))
        return path

    def _svc(self, session) -> LibraryQueryService:
        return LibraryQueryService(
            ResourceRepository(session),
            TaskSummaryRepository(session),
            file_ops=self.ops,
            store_root=self.store,
        )

    async def _import_image(self, session, name: str = "a.png", seed: int = 0) -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id=f"j-{name}")
        await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
            job, ResourceType.IMAGE, "file", [str(self._png(name, seed))]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    def _collection_svc(self, session) -> CollectionService:
        return CollectionService(CollectionRepository(session), ResourceRepository(session))

    async def test_batch_add_tags_creates_and_is_idempotent(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            svc = self._svc(session)
            first = await svc.batch("add_tags", [rid], ["coserA"])
            second = await svc.batch("add_tags", [rid], ["coserA", "coserB"])
            self.assertEqual(first.ok, [rid])
            self.assertEqual(second.ok, [rid])
            tags = (await ResourceRepository(session).get(rid)).tags
            names = sorted(tag.name for tag in tags)
            self.assertEqual(names, ["coserA", "coserB"])

    async def test_batch_add_tags_empty_names_fails(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            result = await self._svc(session).batch("add_tags", [rid], ["  "])
            self.assertEqual(result.ok, [])
            self.assertEqual(result.failed[0].message, "empty tags")

    async def test_batch_add_tags_partial(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            result = await self._svc(session).batch("add_tags", [rid, 99999], ["t"])
            self.assertEqual(result.ok, [rid])
            self.assertEqual([row.id for row in result.failed], [99999])

    def test_batch_request_schema_accepts_add_tags(self) -> None:
        body = ResourceBatchRequest(action="add_tags", ids=[1], tag_names=["t"])
        self.assertEqual(body.tag_names, ["t"])

    async def test_batch_add_items_is_idempotent_and_skips_duplicates(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", seed=1)
            b = await self._import_image(session, "b.png", seed=2)
            collections = self._collection_svc(session)
            created = await collections.create("批量加入", None)
            assert created.id is not None

            first = await collections.add_items(created.id, [a, b, a, 99999])
            self.assertEqual(first, (2, 0, 1))
            second = await collections.add_items(created.id, [a, b])
            self.assertEqual(second, (0, 2, 0))

            members = await collections.members(created.id)
            self.assertEqual([item.id for item in members], [a, b])

    async def test_export_copies_members_with_order_names(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", seed=1)
            b = await self._import_image(session, "b.png", seed=2)
            collections = self._collection_svc(session)
            created = await collections.create("C104 返图", None)
            assert created.id is not None
            await collections.add_item(created.id, a)
            await collections.add_item(created.id, b)
            target = self.root / "out"
            target.mkdir()
            result = await collections.export(created.id, str(target))
            self.assertEqual(result.exported, 2)
            self.assertEqual(result.skipped, 0)
            files = sorted(p.name for p in target.iterdir())
            self.assertEqual(files, ["001_a.png", "002_b.png"])

    async def test_export_skips_missing_primary(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            collections = self._collection_svc(session)
            created = await collections.create("合集", None)
            assert created.id is not None
            await collections.add_item(created.id, rid)
            pkg = ResourcePackage(self.store, ResourceType.IMAGE, rid, self.ops, cover_falls_back_to_primary=True)
            primary = next(p for p in pkg.root.iterdir() if p.name == "primary.png")
            primary.unlink()
            target = self.root / "out"
            target.mkdir()
            result = await collections.export(created.id, str(target))
            self.assertEqual(result.exported, 0)
            self.assertEqual(result.skipped, 1)

    async def test_export_empty_collection_raises(self) -> None:
        async with self.factory() as session:
            collections = self._collection_svc(session)
            created = await collections.create("空合集", None)
            assert created.id is not None
            target = self.root / "out"
            target.mkdir()
            with self.assertRaises(HTTPException) as ctx:
                await collections.export(created.id, str(target))
            self.assertEqual(ctx.exception.status_code, 422)

    async def test_export_bad_target_raises(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            collections = self._collection_svc(session)
            created = await collections.create("合集", None)
            assert created.id is not None
            await collections.add_item(created.id, rid)
            with self.assertRaises(HTTPException) as ctx:
                await collections.export(created.id, str(self.root / "nope"))
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_list_hides_collection_members_by_default(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", seed=1)
            b = await self._import_image(session, "b.png", seed=2)
            collections = self._collection_svc(session)
            created = await collections.create("合集", None)
            assert created.id is not None
            await collections.add_item(created.id, a)
            svc = self._svc(session)

            page = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc",
            )
            ids = {item.id for item in page.items}
            self.assertNotIn(a, ids)
            self.assertIn(b, ids)
            self.assertEqual(page.total, 1)

            with_all = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc",
                include_collected=True,
            )
            self.assertEqual({item.id for item in with_all.items}, {a, b})

            search = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc", q="a",
            )
            self.assertIn(a, {item.id for item in search.items})

    async def test_list_mixed_excludes_collected_resources(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", seed=1)
            b = await self._import_image(session, "b.png", seed=2)
            collections = self._collection_svc(session)
            created = await collections.create("合集", None)
            assert created.id is not None
            await collections.add_item(created.id, a)
            svc = self._svc(session)

            page = await svc.list_page(
                None, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc",
            )
            resource_ids = {
                item.id for item in page.items if not isinstance(item, dict)
            }
            self.assertNotIn(a, resource_ids)
            self.assertIn(b, resource_ids)
            self.assertTrue(any(isinstance(item, dict) for item in page.items))
            self.assertEqual(page.total, 2)

            with_all = await svc.list_page(
                None, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc",
                include_collected=True,
            )
            self.assertEqual(with_all.total, 3)

    async def test_stats_excludes_collected_from_by_type(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", seed=1)
            await self._import_image(session, "b.png", seed=2)
            collections = self._collection_svc(session)
            created = await collections.create("合集", None)
            assert created.id is not None
            await collections.add_item(created.id, a)
            stats = await ResourceRepository(session).stats()
            self.assertEqual(stats["by_type"].get("image"), 1)

    async def test_trash_list_still_shows_collection_members(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", seed=1)
            collections = self._collection_svc(session)
            created = await collections.create("合集", None)
            assert created.id is not None
            await collections.add_item(created.id, a)
            svc = self._svc(session)
            await svc.trash(a)
            page = await svc.list_page(
                None, ResourceStatus.TRASHED, 50, 0,
                ResourceSortField.CREATED_AT, "desc",
            )
            self.assertIn(a, {item.id for item in page.items})

    def test_export_endpoint_404_unknown_collection(self) -> None:
        with patch.object(settings, "db_path", self.db_path):
            with TestClient(app) as client:
                res = client.post("/library/collections/99999/export", json={"targetDir": "C:/x"})
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
