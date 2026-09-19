"""列表搜索、排序、标签 AND、非法 sort。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.schemas import ResourcePatch, ResourceSortField
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.main import app
from app.shared.db.migrations import migrate
from app.shared.models import Resource, ResourceStatus, ResourceType


class LibrarySearchSortTests(unittest.IsolatedAsyncioTestCase):
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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    def _svc(self, session) -> LibraryQueryService:
        return LibraryQueryService(ResourceRepository(session), TaskSummaryRepository(session))

    async def test_title_like_and_title_sort(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            await repo.create(Resource(type=ResourceType.IMAGE, title="海边日落", status=ResourceStatus.ACTIVE))
            await repo.create(Resource(type=ResourceType.IMAGE, title="山间", status=ResourceStatus.ACTIVE))
            svc = self._svc(session)
            page = await svc.list_page(
                ResourceType.IMAGE,
                ResourceStatus.ACTIVE,
                80,
                0,
                ResourceSortField.TITLE,
                "asc",
                q="海边",
            )
            self.assertEqual([item.title for item in page.items], ["海边日落"])
            all_page = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 80, 0, ResourceSortField.TITLE, "asc"
            )
            self.assertEqual([item.title for item in all_page.items], ["山间", "海边日落"])

    async def test_tag_and_and_q_hits_tag_name(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            a = await repo.create(Resource(type=ResourceType.IMAGE, title="A", status=ResourceStatus.ACTIVE))
            b = await repo.create(Resource(type=ResourceType.IMAGE, title="B", status=ResourceStatus.ACTIVE))
            svc = self._svc(session)
            await svc.patch(a.id, ResourcePatch(tag_names=["夜景", "海"]))
            await svc.patch(b.id, ResourcePatch(tag_names=["夜景"]))
            tags = await repo.list_tags()
            by_name = {t.name: t.id for t in tags if t.id is not None}
            both = await svc.list_page(
                ResourceType.IMAGE,
                ResourceStatus.ACTIVE,
                80,
                0,
                ResourceSortField.CREATED_AT,
                "desc",
                tag_ids=[by_name["夜景"], by_name["海"]],
            )
            self.assertEqual([item.title for item in both.items], ["A"])
            named = await svc.list_page(
                ResourceType.IMAGE,
                ResourceStatus.ACTIVE,
                80,
                0,
                ResourceSortField.CREATED_AT,
                "desc",
                q="海",
            )
            self.assertEqual({item.title for item in named.items}, {"A"})

    async def test_filename_like(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            row = await repo.create(Resource(type=ResourceType.IMAGE, title="x", status=ResourceStatus.ACTIVE))
            await repo.add_file(
                row.id,
                path=str(self.root / "vacation.jpg"),
                sha256=None,
                size=10,
                format_="jpg",
                role="primary",
            )
            svc = self._svc(session)
            page = await svc.list_page(
                ResourceType.IMAGE,
                ResourceStatus.ACTIVE,
                80,
                0,
                ResourceSortField.CREATED_AT,
                "desc",
                q="vacation",
            )
            self.assertEqual(len(page.items), 1)

    async def test_size_sort_nulls_last(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            small = await repo.create(Resource(type=ResourceType.IMAGE, title="small", status=ResourceStatus.ACTIVE))
            await repo.create(Resource(type=ResourceType.IMAGE, title="empty", status=ResourceStatus.ACTIVE))
            await repo.add_file(
                small.id, path=str(self.root / "s.jpg"), sha256=None, size=3, format_="jpg", role="primary"
            )
            svc = self._svc(session)
            page = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 80, 0, ResourceSortField.SIZE, "desc"
            )
            self.assertEqual(page.items[0].title, "small")
            self.assertEqual(page.items[-1].title, "empty")

    async def test_duration_forbidden_on_image(self) -> None:
        async with self.factory() as session:
            svc = self._svc(session)
            with self.assertRaises(HTTPException) as ctx:
                await svc.list_page(
                    ResourceType.IMAGE, ResourceStatus.ACTIVE, 80, 0, ResourceSortField.DURATION, "desc"
                )
            self.assertEqual(ctx.exception.status_code, 422)

    async def test_duration_allowed_on_video(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            long = await repo.create(Resource(type=ResourceType.VIDEO, title="long", status=ResourceStatus.ACTIVE))
            short = await repo.create(Resource(type=ResourceType.VIDEO, title="short", status=ResourceStatus.ACTIVE))
            await repo.add_file(
                long.id, path="a.mp4", sha256=None, size=1, format_="mp4", role="primary", duration=100
            )
            await repo.add_file(
                short.id, path="b.mp4", sha256=None, size=1, format_="mp4", role="primary", duration=10
            )
            svc = self._svc(session)
            page = await svc.list_page(
                ResourceType.VIDEO, ResourceStatus.ACTIVE, 80, 0, ResourceSortField.DURATION, "asc"
            )
            self.assertEqual([item.title for item in page.items], ["short", "long"])

    def test_http_duration_on_image_is_422(self) -> None:
        client = TestClient(app)
        response = client.get("/library/resources", params={"type": "image", "sort": "duration"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
