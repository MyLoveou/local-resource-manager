"""分类树、多分类筛选、保存时间线与首页聚合。"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.schemas import (
    ResourcePatch,
    ResourceSortField,
    SavedViewCreate,
    SavedViewFilters,
)
from app.library.application.photos import PhotoTimelineService
from app.library.application.use_cases import (
    CategoryService,
    CollectionService,
    LibraryQueryService,
    SavedViewService,
)
from app.library.domain.models import CategoryRule, Resource, ResourceStatus, ResourceType
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import (
    CategoryRepository,
    CollectionRepository,
    ResourceRepository,
    SavedViewRepository,
    TaskSummaryRepository,
)
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps


class LibraryWorkspaceTests(unittest.IsolatedAsyncioTestCase):
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

    def _png(self, name: str, seed: int = 0) -> Path:
        path = self.root / f"{Path(name).stem}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        color = ((seed * 61) % 256, (seed * 89) % 256, (seed * 31) % 256)
        Image.new("RGB", (8, 8), color).save(path, format="PNG")
        return path

    async def _import_image(self, session, name: str, seed: int = 0) -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id=f"j-{name}-{seed}")
        await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
            job, ResourceType.IMAGE, "file", [str(self._png(name, seed))]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    def _categories(self, session) -> CategoryService:
        return CategoryService(CategoryRepository(session), SavedViewRepository(session))

    def _query(self, session) -> LibraryQueryService:
        return LibraryQueryService(
            ResourceRepository(session),
            TaskSummaryRepository(session),
            file_ops=self.ops,
            store_root=self.store,
        )

    async def test_tree_depth_cycle_and_delete_protection(self) -> None:
        async with self.factory() as session:
            categories = self._categories(session)
            root = await categories.create(ResourceType.IMAGE, None, "二次元", 0)
            child = await categories.create(ResourceType.IMAGE, root.id, "角色", 0)
            await categories.create(ResourceType.IMAGE, child.id, "初音", 0)

            deep = await categories.create(ResourceType.IMAGE, None, "深层", 0)
            level2 = await categories.create(ResourceType.IMAGE, deep.id, "二级", 0)
            level3 = await categories.create(ResourceType.IMAGE, level2.id, "三级", 0)
            level4 = await categories.create(ResourceType.IMAGE, level3.id, "四级", 0)
            with self.assertRaises(HTTPException) as depth:
                await categories.create(ResourceType.IMAGE, level4.id, "五级", 0)
            self.assertEqual(depth.exception.status_code, 422)

            with self.assertRaises(HTTPException) as cycle:
                await categories.patch(
                    root.id, name=None, parent_id=child.id, update_parent=True, sort=None
                )
            self.assertEqual(cycle.exception.status_code, 409)

            with self.assertRaises(HTTPException) as children:
                await categories.delete(root.id)
            self.assertEqual(children.exception.status_code, 409)

            empty = await categories.create(ResourceType.IMAGE, None, "待删", 0)
            await categories.delete(empty.id)
            tree = await categories.tree(ResourceType.IMAGE)
            self.assertEqual([node.name for node in tree], ["二次元", "深层"])
            self.assertEqual(tree[0].children[0].name, "角色")

    async def test_multi_category_assignment_and_subtree_filter(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", 1)
            b = await self._import_image(session, "b.png", 2)
            categories = self._categories(session)
            anime = await categories.create(ResourceType.IMAGE, None, "二次元", 0)
            role = await categories.create(ResourceType.IMAGE, anime.id, "角色", 0)
            scenery = await categories.create(ResourceType.IMAGE, None, "风景", 0)
            query = self._query(session)

            await query.patch(a, ResourcePatch(category_ids=[role.id, scenery.id]))
            await query.patch(b, ResourcePatch(category_ids=[anime.id]))

            page = await query.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc", category_ids=[anime.id],
            )
            self.assertEqual({item.id for item in page.items}, {a, b})
            self.assertEqual(page.total, 2)

            scenery_page = await query.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc", category_ids=[scenery.id],
            )
            self.assertEqual({item.id for item in scenery_page.items}, {a})

            await query.patch(b, ResourcePatch(category_ids=[]))
            uncategorized = await query.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc", uncategorized=True,
            )
            self.assertEqual({item.id for item in uncategorized.items}, {b})

    async def test_batch_add_and_remove_categories(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", 1)
            b = await self._import_image(session, "b.png", 2)
            category = await self._categories(session).create(
                ResourceType.IMAGE, None, "批量", 0
            )
            query = self._query(session)
            added = await query.batch("add_categories", [a, b], category_ids=[category.id])
            self.assertEqual(added.ok, [a, b])
            self.assertEqual(
                sorted(
                    item.id
                    for item in (await ResourceRepository(session).get(a)).categories
                ),
                [category.id],
            )
            removed = await query.batch("remove_categories", [a], category_ids=[category.id])
            self.assertEqual(removed.ok, [a])
            self.assertEqual((await ResourceRepository(session).get(a)).categories, [])

    async def test_import_applies_categories_and_tags(self) -> None:
        async with self.factory() as session:
            category = await self._categories(session).create(
                ResourceType.IMAGE, None, "导入分类", 0
            )
            job = ImportJobState(id="import-meta")
            await ImportService(
                ResourceRepository(session), store_root=self.store, file_ops=self.ops
            ).run(
                job,
                ResourceType.IMAGE,
                "file",
                [str(self._png("import-meta.png", 9))],
                category_ids=[category.id],
                tag_names=["coser", "返图"],
            )
            self.assertEqual(job.imported, 1)
            items = await ResourceRepository(session).list(ResourceType.IMAGE, None, 10, 0, "desc")
            resource = await ResourceRepository(session).get(items[0].id)
            self.assertEqual([item.name for item in resource.categories], ["导入分类"])
            self.assertEqual(sorted(item.name for item in resource.tags), ["coser", "返图"])
            counts = await CategoryRepository(session).counts(ResourceType.IMAGE)
            self.assertEqual(counts.get(category.id), 1)

    async def test_saved_view_and_category_delete_cleanup(self) -> None:
        async with self.factory() as session:
            categories = self._categories(session)
            root = await categories.create(ResourceType.IMAGE, None, "漫展", 0)
            child = await categories.create(ResourceType.IMAGE, root.id, "C104", 0)
            views = SavedViewService(SavedViewRepository(session), CategoryRepository(session))
            created = await views.create(SavedViewCreate(
                scope="image",
                name="2026 漫展",
                filters=SavedViewFilters(
                    image=CategoryRule(include=[root.id, child.id]),
                ),
            ))
            self.assertEqual(created.filters.image.include, [root.id, child.id])

            await categories.delete(child.id)
            refreshed = await views.list("image")
            self.assertEqual(refreshed[0].filters.image.include, [root.id])

            with self.assertRaises(HTTPException) as duplicate:
                await views.create(SavedViewCreate(
                    scope="image",
                    name="2026 漫展",
                    filters=SavedViewFilters(),
                ))
            self.assertEqual(duplicate.exception.status_code, 409)

    async def test_media_timeline_and_exclusion(self) -> None:
        async with self.factory() as session:
            image_a = await self._import_image(session, "a.png", 1)
            image_b = await self._import_image(session, "b.png", 2)
            repo = ResourceRepository(session)
            video = await repo.create(
                Resource(type=ResourceType.VIDEO, title="clip", status=ResourceStatus.ACTIVE)
            )
            assert video.id is not None
            await repo.add_file(
                video.id,
                path=str(self.root / "clip.mp4"),
                sha256="v" * 64,
                size=1024,
                format_="mp4",
                role="primary",
                exif_taken_at="2026-10-17T09:00:00",
            )
            for rid in (image_a, image_b):
                primary = await repo.get_file_by_role(rid, "primary")
                assert primary is not None
                await repo.update_file_exif(primary.id, taken_at="2026-10-17T10:00:00", lat=None, lng=None)
            await repo.commit()

            categories = self._categories(session)
            keep = await categories.create(ResourceType.IMAGE, None, "保留", 0)
            drop = await categories.create(ResourceType.IMAGE, None, "排除", 0)
            await self._query(session).patch(image_a, ResourcePatch(category_ids=[keep.id]))
            await self._query(session).patch(image_b, ResourcePatch(category_ids=[drop.id]))

            timeline = PhotoTimelineService(repo)
            only_keep = await timeline.timeline(
                include_all=False,
                scope="image",
                year=None,
                month=None,
                image_rule=CategoryRule(include=[keep.id]),
            )
            self.assertEqual(only_keep.total, 1)

            excluded = await timeline.timeline(
                include_all=False,
                scope="image",
                year=None,
                month=None,
                image_rule=CategoryRule(include=[keep.id], exclude=[keep.id]),
            )
            self.assertEqual(excluded.total, 0)

            media = await timeline.timeline(
                include_all=False,
                scope="media",
                year=None,
                month=None,
                image_rule=CategoryRule(include=[keep.id]),
            )
            self.assertEqual(media.total, 2)
            self.assertEqual({tile.kind for day in media.days for tile in day.photos}, {"image", "video"})

    async def test_home_and_collection_previews(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, "a.png", 1)
            b = await self._import_image(session, "b.png", 2)
            collections = CollectionService(
                CollectionRepository(session), ResourceRepository(session)
            )
            created = await collections.create("返图", None)
            assert created.id is not None
            await collections.add_items(created.id, [a, b])
            category = await self._categories(session).create(
                ResourceType.IMAGE, None, "漫展", 0
            )
            await self._query(session).patch(a, ResourcePatch(category_ids=[category.id]))
            members = await collections.members(created.id)
            self.assertEqual([item.id for item in members], [a, b])
            self.assertEqual([item.name for item in members[0].categories or []], ["漫展"])
            home = await self._query(session).home()
            self.assertEqual(len(home.recent), 2)
            self.assertEqual(len(home.collections), 1)
            self.assertEqual(home.collections[0].member_count, 2)
            self.assertEqual(len(home.collections[0].preview_thumbnails), 2)


if __name__ == "__main__":
    unittest.main()
