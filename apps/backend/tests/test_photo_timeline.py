"""照片时间线：分组/可见性/日过滤/回填/GPS 解析。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.media_probe import _gps_coord, _parse_iso6709, _video_gps, _video_taken_at
from app.library.application.photos import PhotoTimelineService
from app.library.application.schemas import ResourcePatch, ResourceSortField, SavedViewCreate
from app.library.application.use_cases import LibraryQueryService, SavedViewService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import (
    CategoryRepository,
    ResourceRepository,
    SavedViewRepository,
    TaskSummaryRepository,
)
from app.library.domain.models import Resource, ResourceStatus, ResourceType
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class PhotoTimelineTests(unittest.IsolatedAsyncioTestCase):
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
        # 生成最小尺寸的 JPEG，仅用于计算 sha256 去重
        path = self.root / (name.rsplit(".", 1)[0] + ".jpg")
        path.parent.mkdir(parents=True, exist_ok=True)
        color = ((seed * 60) % 256, (seed * 90) % 256, (seed * 30) % 256)
        Image.new("RGB", (4, 4), color).save(path, format="JPEG")
        return path

    def _jpeg_with_taken_at(self, name: str, taken_at: str) -> Path:
        path = self.root / name
        image = Image.new("RGB", (4, 4), (120, 30, 200))
        exif = Image.Exif()
        exif[36867] = taken_at
        image.save(path, format="JPEG", exif=exif)
        return path

    async def _import_image(self, session, path: Path) -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id=f"j-{path.name}")
        await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
            job, ResourceType.IMAGE, "file", [str(path)]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    def _query(self, session) -> LibraryQueryService:
        return LibraryQueryService(
            ResourceRepository(session),
            TaskSummaryRepository(session),
            file_ops=self.ops,
            store_root=self.store,
        )

    def _photos(self, session) -> PhotoTimelineService:
        return PhotoTimelineService(ResourceRepository(session))

    async def test_gps_coord_parser(self) -> None:
        self.assertAlmostEqual(_gps_coord((31, 12, 30), "N"), 31.2083333, places=5)
        self.assertAlmostEqual(_gps_coord((31, 12, 30), "S"), -31.2083333, places=5)
        self.assertAlmostEqual(_gps_coord((121, 30, 0), "W"), -121.5, places=5)
        self.assertIsNone(_gps_coord((1, 2), "N"))
        self.assertIsNone(_gps_coord((1, 2, 3), None))

    async def test_timeline_groups_days_and_unknown(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, self._png("a.png", 1))
            b = await self._import_image(session, self._png("b.png", 2))
            c = await self._import_image(session, self._png("c.png", 3))
            repo = ResourceRepository(session)
            svc = self._query(session)
            fa = await repo.get_file_by_role(a, "primary")
            fb = await repo.get_file_by_role(b, "primary")
            assert fa is not None and fb is not None
            await repo.update_file_exif(fa.id, taken_at="2026-10-17T10:00:00", lat=31.2, lng=121.5)
            await repo.update_file_exif(fb.id, taken_at="2026-10-17T18:30:00", lat=None, lng=None)
            await repo.commit()
            await svc.patch(c, ResourcePatch(timeline_visible=True))

            photos = self._photos(session)
            default = await photos.timeline(
                include_all=False, type_=ResourceType.IMAGE, year=None, month=None,
                category_ids=None, tag_ids=None,
            )
            self.assertEqual(default.days[0].date, "2026-10-17")
            self.assertEqual(default.days[0].count, 2)
            self.assertEqual(len(default.days[0].photos), 2)
            self.assertIsNotNone(default.days[0].photos[0].thumbnail_path)
            self.assertEqual(default.unknown_count, 0)
            self.assertEqual(len(default.unknown_photos), 0)
            self.assertEqual(default.total, 2)

            with_unknown = await photos.timeline(
                include_all=False, type_=ResourceType.IMAGE, year=None, month=None,
                category_ids=None, tag_ids=None, include_untimed=True,
            )
            self.assertEqual(with_unknown.unknown_count, 1)
            self.assertEqual(len(with_unknown.unknown_photos), 1)
            self.assertEqual(with_unknown.total, 3)

            all_photos = await photos.timeline(
                include_all=True, type_=ResourceType.IMAGE, year=None, month=None,
                category_ids=None, tag_ids=None, include_untimed=True,
            )
            self.assertEqual(all_photos.days[0].count, 2)
            self.assertEqual(all_photos.unknown_count, 1)
            self.assertEqual(all_photos.total, 3)

    async def test_visibility_tristate(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, self._png("a.png", 1))
            b = await self._import_image(session, self._png("b.png", 2))
            repo = ResourceRepository(session)
            svc = self._query(session)
            for rid, day in ((a, "2026-10-17T10:00:00"), (b, "2026-10-18T10:00:00")):
                file_row = await repo.get_file_by_role(rid, "primary")
                await repo.update_file_exif(file_row.id, taken_at=day, lat=None, lng=None)
            await repo.commit()
            await svc.patch(b, ResourcePatch(timeline_visible=False))

            page = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc", timeline_visible=True,
            )
            self.assertEqual({item.id for item in page.items}, {a})

            hidden = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc", timeline_visible=False,
            )
            self.assertEqual({item.id for item in hidden.items}, {b})

    async def test_day_filter_matches_timeline(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, self._png("a.png", 1))
            b = await self._import_image(session, self._png("b.png", 2))
            repo = ResourceRepository(session)
            svc = self._query(session)
            fa = await repo.get_file_by_role(a, "primary")
            fb = await repo.get_file_by_role(b, "primary")
            await repo.update_file_exif(fa.id, taken_at="2026-10-17T10:00:00", lat=None, lng=None)
            await repo.update_file_exif(fb.id, taken_at="2026-10-18T10:00:00", lat=None, lng=None)
            await repo.commit()

            page = await svc.list_page(
                ResourceType.IMAGE, ResourceStatus.ACTIVE, 50, 0,
                ResourceSortField.CREATED_AT, "desc",
                taken_date="2026-10-17", timeline_visible=True,
            )
            self.assertEqual({item.id for item in page.items}, {a})
            self.assertEqual(page.total, 1)

    async def test_video_taken_at_parser(self) -> None:
        self.assertEqual(_video_taken_at("2026-10-17 12:34:56"), "2026-10-17T12:34:56")
        self.assertEqual(_video_taken_at("2026-10-17T12:34:56.000000Z")[5:10], "10-17")
        self.assertIsNone(_video_taken_at(None))
        self.assertIsNone(_video_taken_at("not-a-time"))

    async def test_video_location_parser(self) -> None:
        self.assertEqual(
            _parse_iso6709("+31.2304+121.4737+010.000/"),
            (31.2304, 121.4737),
        )
        self.assertEqual(_parse_iso6709("31.2304,121.4737"), (31.2304, 121.4737))
        self.assertEqual(_video_gps({"location": "+31.2304+121.4737/"}), (31.2304, 121.4737))
        self.assertEqual(_video_gps({"Location": "+0+0/"}), (None, None))

    async def test_timeline_includes_video_tiles(self) -> None:
        async with self.factory() as session:
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
                width=1920,
                height=1080,
                duration=12.5,
                exif_taken_at="2026-10-17T09:00:00",
            )
            await repo.commit()
            photos = await self._photos(session).timeline(
                include_all=False, type_=ResourceType.VIDEO, year=None, month=None, category_ids=None, tag_ids=None
            )
            self.assertEqual(photos.total, 1)
            tile = photos.days[0].photos[0]
            self.assertEqual(tile.kind, "video")
            self.assertEqual(tile.duration, 12.5)
            self.assertEqual(tile.width, 1920)

    async def test_import_can_exclude_from_timeline(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j-no-timeline")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job,
                ResourceType.IMAGE,
                "file",
                [str(self._png("not-in-timeline.png", 7))],
                timeline_visible=False,
            )
            self.assertEqual(job.imported, 1)
            items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
            self.assertFalse(items[0].timeline_visible)
            photos = await self._photos(session).timeline(
                include_all=False, type_=ResourceType.IMAGE, year=None, month=None, category_ids=None, tag_ids=None
            )
            self.assertEqual(photos.total, 0)

    async def test_map_visibility_is_independent_from_timeline(self) -> None:
        async with self.factory() as session:
            a = await self._import_image(session, self._png("map-a.png", 1))
            b = await self._import_image(session, self._png("map-b.png", 2))
            repo = ResourceRepository(session)
            svc = self._query(session)
            fa = await repo.get_file_by_role(a, "primary")
            fb = await repo.get_file_by_role(b, "primary")
            assert fa is not None and fb is not None
            await repo.update_file_exif(
                fa.id, taken_at="2026-10-17T10:00:00", lat=31.23, lng=121.47
            )
            await repo.update_file_exif(
                fb.id, taken_at="2026-10-18T10:00:00", lat=None, lng=None
            )
            await repo.commit()
            await svc.patch(a, ResourcePatch(timeline_visible=False))

            photos = self._photos(session)
            points = await photos.timeline(
                include_all=True,
                type_=ResourceType.IMAGE,
                year=None,
                month=None,
                category_ids=None,
                tag_ids=None,
                include_untimed=True,
                map_visible=True,
                map_only=True,
            )
            self.assertEqual({point.id for point in points.unknown_photos}, set())
            self.assertEqual(
                {photo.id for day in points.days for photo in day.photos}, {a}
            )

            await svc.patch(a, ResourcePatch(map_visible=False))
            hidden = await photos.timeline(
                include_all=True,
                type_=ResourceType.IMAGE,
                year=None,
                month=None,
                category_ids=None,
                tag_ids=None,
                include_untimed=True,
                map_visible=True,
                map_only=True,
            )
            self.assertEqual(hidden.total, 0)

    async def test_import_can_exclude_from_map(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="j-no-map")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job,
                ResourceType.IMAGE,
                "file",
                [str(self._png("not-in-map.png", 8))],
                map_visible=False,
            )
            self.assertEqual(job.imported, 1)
            items = await repo.list(ResourceType.IMAGE, None, 10, 0, "desc")
            self.assertFalse(items[0].map_visible)

    async def test_saved_views_keep_map_kind_separate(self) -> None:
        async with self.factory() as session:
            views = SavedViewService(SavedViewRepository(session), CategoryRepository(session))
            await views.create(SavedViewCreate(kind="map", scope="image", name="旅行地图"))
            await views.create(SavedViewCreate(kind="timeline", scope="image", name="旅行时间线"))
            map_views = await views.list(None, "map")
            timeline_views = await views.list(None, "timeline")
            self.assertEqual([view.name for view in map_views], ["旅行地图"])
            self.assertEqual([view.name for view in timeline_views], ["旅行时间线"])

    async def test_backfill_reads_exif_and_keeps_visibility(self) -> None:
        async with self.factory() as session:
            path = self._jpeg_with_taken_at("shot.jpg", "2026:10:17 12:34:56")
            rid = await self._import_image(session, path)
            repo = ResourceRepository(session)
            file_row = await repo.get_file_by_role(rid, "primary")
            assert file_row is not None
            await repo.update_file_exif(file_row.id, taken_at=None, lat=None, lng=None)
            await repo.commit()
            await self._query(session).patch(rid, ResourcePatch(timeline_visible=False))

            result = await self._photos(session).backfill()
            self.assertGreaterEqual(result.scanned, 1)
            self.assertGreaterEqual(result.taken_at_updated, 1)
            updated = await ResourceRepository(session).get_file_by_role(rid, "primary")
            assert updated is not None
            self.assertEqual(updated.exif_taken_at, "2026-10-17T12:34:56")
            row = await ResourceRepository(session).get(rid)
            assert row is not None
            self.assertFalse(row.timeline_visible)


if __name__ == "__main__":
    unittest.main()
