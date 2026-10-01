"""列表 keyset、导入工人池、媒体缓存头。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.schemas import ResourceSortField
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.library.domain.models import (
    Resource,
    ResourceStatus,
    ResourceType,
)

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class AppPerformanceTests(unittest.IsolatedAsyncioTestCase):
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
        def _pragmas(dbapi_conn, _record) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA busy_timeout=5000")
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
        path.write_bytes(_PNG + name.encode("utf-8"))
        return path

    async def test_keyset_pages(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            for title in ("a", "b", "c"):
                await repo.create(Resource(type=ResourceType.IMAGE, title=title, status=ResourceStatus.ACTIVE))
            svc = LibraryQueryService(repo, TaskSummaryRepository(session))
            first = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 2, 0, ResourceSortField.CREATED_AT, "desc"
            )
            self.assertEqual(len(first.items), 2)
            self.assertTrue(first.has_more)
            self.assertIsNotNone(first.next_id)
            second = await svc.list_page(
                ResourceType.IMAGE,
                ResourceStatus.ACTIVE,
                2,
                0,
                ResourceSortField.CREATED_AT,
                "desc",
                after_created_at=first.next_created_at,
                after_id=first.next_id,
            )
            self.assertEqual(len(second.items), 1)
            self.assertFalse(second.has_more)
            ids = {item.id for item in first.items} | {item.id for item in second.items}
            self.assertEqual(len(ids), 3)

    async def test_import_pool(self) -> None:
        files = [self._png(f"{i}.png") for i in range(3)]
        job = ImportJobState(id="pool")
        service = ImportService(
            session_factory=self.factory,
            store_root=self.store,
            file_ops=self.ops,
            workers=2,
        )
        await service.run(job, ResourceType.IMAGE, "file", [str(p) for p in files])
        self.assertEqual(job.imported, 3)
        self.assertEqual(job.done, 3)
        async with self.factory() as session:
            self.assertEqual(await ResourceRepository(session).count(ResourceType.IMAGE), 3)


if __name__ == "__main__":
    unittest.main()
