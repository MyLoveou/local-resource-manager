"""Person/cosplayer dimension tests."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.photos import PhotoTimelineService
from app.library.domain.models import Resource, ResourceStatus, ResourceType
from app.library.infrastructure.repositories import PersonRepository, ResourceRepository
from app.shared.db.migrations import migrate


class PersonTests(unittest.IsolatedAsyncioTestCase):
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

    async def _resource(self, session, title: str) -> int:
        repo = ResourceRepository(session)
        resource = await repo.create(Resource(type=ResourceType.IMAGE, title=title, status=ResourceStatus.ACTIVE))
        assert resource.id is not None
        await repo.add_file(
            resource.id,
            path=str(self.root / f"{title}.jpg"),
            sha256=f"{title:0<64}"[:64],
            size=3,
            format_="jpg",
            role="primary",
            exif_taken_at="2026-10-17T10:00:00",
        )
        return resource.id

    async def test_person_aliases_links_and_merge(self) -> None:
        async with self.factory() as session:
            repo = PersonRepository(session)
            first = await repo.create("Coser A", "简介", None, ["A", "小 A"])
            second = await repo.create("Coser A 旧", None, None, ["旧名"])
            assert first.id is not None and second.id is not None
            rid = await self._resource(session, "photo")
            await repo.add_resources([rid], [first.id, second.id])
            detail = await ResourceRepository(session).get(rid)
            assert detail is not None
            self.assertEqual({person.id for person in (detail.persons or [])}, {first.id, second.id})
            found = await repo.list("小 A")
            self.assertEqual([item.id for item in found], [first.id])
            self.assertEqual(found[0].resource_count, 1)
            merged = await repo.merge(first.id, second.id)
            assert merged is not None
            self.assertEqual(set(merged.aliases), {"A", "小 A", "旧名", "Coser A 旧"})
            rows = await ResourceRepository(session).list(
                ResourceType.IMAGE, None, 10, 0, "desc", person_ids=[first.id]
            )
            self.assertEqual([row.id for row in rows], [rid])

    async def test_person_filters_timeline(self) -> None:
        async with self.factory() as session:
            repo = PersonRepository(session)
            person = await repo.create("Coser B", None, None, [])
            assert person.id is not None
            rid = await self._resource(session, "mapped")
            await repo.add_resources([rid], [person.id])
            photos = await PhotoTimelineService(ResourceRepository(session)).timeline(
                include_all=True,
                type_=ResourceType.IMAGE,
                year=None,
                month=None,
                category_ids=None,
                tag_ids=None,
                include_untimed=True,
                person_ids=[person.id],
            )
            self.assertEqual(photos.total, 1)
            self.assertEqual(photos.days[0].photos[0].id, rid)
