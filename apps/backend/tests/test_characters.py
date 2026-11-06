"""Character/work dimension tests."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.photos import PhotoTimelineService
from app.library.application.use_cases import LibraryQueryService
from app.library.domain.models import Resource, ResourceStatus, ResourceType
from app.library.infrastructure.repositories import (
    CharacterRepository,
    ResourceRepository,
    TaskSummaryRepository,
)
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps


class CharacterTests(unittest.IsolatedAsyncioTestCase):
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

    async def _create_resource(self, session, title: str) -> int:
        repo = ResourceRepository(session)
        resource = await repo.create(
            Resource(type=ResourceType.IMAGE, title=title, status=ResourceStatus.ACTIVE)
        )
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

    async def test_character_aliases_links_and_merge(self) -> None:
        async with self.factory() as session:
            repo = CharacterRepository(session)
            first = await repo.create("角色 A", "作品 X", "简介", None, ["A", "小 A"])
            second = await repo.create("角色 A 旧", "作品 X", None, None, ["旧名"])
            assert first.id is not None and second.id is not None
            resource_id = await self._create_resource(session, "photo")
            await repo.add_resources([resource_id], [first.id, second.id])

            listed = await repo.list("小 A")
            self.assertEqual([item.id for item in listed], [first.id])
            self.assertEqual(listed[0].resource_count, 1)
            self.assertEqual(listed[0].work_name, "作品 X")

            merged = await repo.merge(first.id, second.id)
            assert merged is not None
            self.assertEqual(merged.aliases, ["A", "小 A", "旧名", "角色 A 旧"])
            self.assertIsNone(await repo.get(second.id))
            resources = await ResourceRepository(session).list(
                ResourceType.IMAGE, None, 10, 0, "desc", character_ids=[first.id]
            )
            self.assertEqual([item.id for item in resources], [resource_id])

    async def test_batch_add_characters(self) -> None:
        async with self.factory() as session:
            repo = CharacterRepository(session)
            character = await repo.create("角色 C", None, None, None, [])
            assert character.id is not None
            resource_id = await self._create_resource(session, "batch")
            service = LibraryQueryService(
                ResourceRepository(session),
                TaskSummaryRepository(session),
            )
            result = await service.batch(
                "add_characters", [resource_id], character_ids=[character.id]
            )
            self.assertEqual(result.ok, [resource_id])
            listed = await ResourceRepository(session).list(
                ResourceType.IMAGE, None, 10, 0, "desc", character_ids=[character.id]
            )
            self.assertEqual([item.id for item in listed], [resource_id])

    async def test_character_filters_timeline(self) -> None:
        async with self.factory() as session:
            repo = CharacterRepository(session)
            character = await repo.create("角色 B", None, None, None, [])
            assert character.id is not None
            resource_id = await self._create_resource(session, "mapped")
            await repo.add_resources([resource_id], [character.id])
            photos = await PhotoTimelineService(ResourceRepository(session)).timeline(
                include_all=True,
                type_=ResourceType.IMAGE,
                year=None,
                month=None,
                category_ids=None,
                tag_ids=None,
                include_untimed=True,
                character_ids=[character.id],
            )
            self.assertEqual(photos.total, 1)
            self.assertEqual(photos.days[0].photos[0].id, resource_id)
