"""回收站：软删、恢复、彻底删除、批量。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.packages.resource_package import ResourcePackage
from app.library.application.schemas import ResourceBatchRequest, ResourceSortField
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.migrations import migrate
from app.shared.errors import InvalidStateError
from app.shared.fs.file_ops import FileOps
from app.shared.models import Resource, ResourceStatus, ResourceType
from fastapi.testclient import TestClient

from app.main import app

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class LibraryTrashTests(unittest.IsolatedAsyncioTestCase):
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

    def _png(self, name: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_PNG)
        return path

    def _svc(self, session) -> LibraryQueryService:
        return LibraryQueryService(
            ResourceRepository(session),
            TaskSummaryRepository(session),
            file_ops=self.ops,
            store_root=self.store,
        )

    async def _import_image(self, session, name: str = "a.png") -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id=f"j-{name}")
        await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
            job, ResourceType.IMAGE, "file", [str(self._png(name))]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    def test_batch_over_limit_schema(self) -> None:
        with self.assertRaises(ValidationError):
            ResourceBatchRequest(action="trash", ids=list(range(1, 202)))

    def test_batch_http_over_limit_422(self) -> None:
        client = TestClient(app)
        res = client.post(
            "/library/resources/batch",
            json={"action": "trash", "ids": list(range(1, 202))},
        )
        self.assertEqual(res.status_code, 422)
        body = res.json()
        self.assertEqual(body["code"], 422)

    async def test_trash_sets_deleted_at_keeps_package(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            pkg = ResourcePackage(self.store, ResourceType.IMAGE, rid, self.ops, cover_falls_back_to_primary=True)
            self.assertTrue(pkg.root.exists())
            updated = await self._svc(session).trash(rid)
            assert updated is not None
            self.assertEqual(updated.status, ResourceStatus.TRASHED)
            self.assertIsNotNone(updated.deleted_at)
            self.assertTrue(pkg.root.exists())

    async def test_trash_idempotent(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            svc = self._svc(session)
            first = await svc.trash(rid)
            second = await svc.trash(rid)
            assert first is not None and second is not None
            self.assertEqual(second.status, ResourceStatus.TRASHED)
            pkg = ResourcePackage(self.store, ResourceType.IMAGE, rid, self.ops, cover_falls_back_to_primary=True)
            self.assertTrue(pkg.root.exists())

    async def test_restore_trashed(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            svc = self._svc(session)
            await svc.trash(rid)
            restored = await svc.restore(rid)
            assert restored is not None
            self.assertEqual(restored.status, ResourceStatus.ACTIVE)
            self.assertIsNone(restored.deleted_at)

    async def test_restore_missing_returns_none(self) -> None:
        async with self.factory() as session:
            self.assertIsNone(await self._svc(session).restore(99999))

    async def test_restore_active_raises(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            with self.assertRaises(InvalidStateError):
                await self._svc(session).restore(rid)

    async def test_purge_drops_row_and_package_keeps_source(self) -> None:
        src = self._png("keep-me.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j-src")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.IMAGE, "file", [str(src)]
            )
            rid = (await repo.list(ResourceType.IMAGE, None, 10, 0, "desc"))[0].id
            assert rid is not None
            pkg = ResourcePackage(self.store, ResourceType.IMAGE, rid, self.ops, cover_falls_back_to_primary=True)
            ok = await self._svc(session).purge(rid)
            self.assertTrue(ok)
            self.assertIsNone(await repo.get(rid))
            self.assertFalse(pkg.root.exists())
            self.assertTrue(src.is_file())

    async def test_purge_disk_failure_keeps_row(self) -> None:
        class BoomOps(FileOps):
            def remove_tree(self, path: Path) -> None:
                raise OSError("locked")

        async with self.factory() as session:
            rid = await self._import_image(session)
            svc = LibraryQueryService(
                ResourceRepository(session),
                TaskSummaryRepository(session),
                file_ops=BoomOps(),
                store_root=self.store,
            )
            with self.assertRaises(RuntimeError):
                await svc.purge(rid)
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            pkg = ResourcePackage(self.store, ResourceType.IMAGE, rid, self.ops, cover_falls_back_to_primary=True)
            self.assertTrue(pkg.root.exists())

    async def test_trash_list_mixes_types(self) -> None:
        async with self.factory() as session:
            image_id = await self._import_image(session)
            repo = ResourceRepository(session)
            video = await repo.create(Resource(type=ResourceType.VIDEO, title="clip", status=ResourceStatus.ACTIVE))
            assert video.id is not None
            svc = self._svc(session)
            await svc.trash(image_id)
            await svc.trash(video.id)
            page = await svc.list_page(None, ResourceStatus.TRASHED, 80, 0, ResourceSortField.CREATED_AT, "desc")
            ids = {item.id for item in page.items}
            self.assertIn(image_id, ids)
            self.assertIn(video.id, ids)

    async def test_batch_trash_partial(self) -> None:
        async with self.factory() as session:
            rid = await self._import_image(session)
            result = await self._svc(session).batch("trash", [rid, 99999])
            self.assertEqual(result.ok, [rid])
            self.assertEqual([row.id for row in result.failed], [99999])
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            self.assertEqual(got.status, ResourceStatus.TRASHED)


if __name__ == "__main__":
    unittest.main()
