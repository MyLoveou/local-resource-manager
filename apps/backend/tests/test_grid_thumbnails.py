"""网格缩略图：导入落盘、失败不挡、字段分离、换封面覆盖。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.schemas import CoverReplace
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.shared.media_types import FILE_ROLE_THUMBNAIL, THUMB_DIR, THUMB_GRID_NAME
from app.shared.models import ResourceType


class GridThumbnailTests(unittest.IsolatedAsyncioTestCase):
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

    def _png(self, name: str, *, size: tuple[int, int] = (64, 48), color: tuple[int, int, int] = (200, 10, 10)) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(path, "PNG")
        return path

    async def _import(self, session, type_: ResourceType, source: Path, **kwargs) -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id="j1")
        await ImportService(repo, store_root=self.store, file_ops=self.ops, **kwargs).run(
            job, type_, "file", [str(source)]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(type_, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    def _thumb_path(self, type_: str, rid: int) -> Path:
        return self.store / type_ / str(rid) / THUMB_DIR / THUMB_GRID_NAME

    async def test_import_image_writes_grid_webp(self) -> None:
        src = self._png("a.png")
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, src)
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            thumbs = [f for f in got.files if f.role == FILE_ROLE_THUMBNAIL]
            self.assertEqual(len(thumbs), 1)
            dest = self._thumb_path("image", rid)
            self.assertTrue(dest.is_file())
            self.assertEqual(Path(thumbs[0].path).resolve(), dest.resolve())
            self.assertFalse((dest.parent.parent / "thumbnail.webp").exists())

    async def test_video_without_cover_skips_thumb(self) -> None:
        video = self.root / "clip.mp4"
        video.write_bytes(b"not-a-real-mp4")
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.VIDEO, video)
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            self.assertFalse(any(f.role == FILE_ROLE_THUMBNAIL for f in got.files))
            self.assertFalse(self._thumb_path("video", rid).exists())

    async def test_thumb_failure_still_imports(self) -> None:
        src = self._png("b.png")
        with patch(
            "app.library.application.thumbnails.write_grid_thumbnail",
            side_effect=OSError("decode failed"),
        ):
            async with self.factory() as session:
                rid = await self._import(session, ResourceType.IMAGE, src)
                got = await ResourceRepository(session).get(rid)
                assert got is not None
                self.assertEqual(got.title, "b")
                self.assertFalse(any(f.role == FILE_ROLE_THUMBNAIL for f in got.files))
                dest = self._thumb_path("image", rid)
                self.assertFalse(dest.exists())

    async def test_thumbnail_path_separate_from_cover(self) -> None:
        src = self._png("c.png")
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, src)
            listed = await ResourceRepository(session).list(ResourceType.IMAGE, None, 10, 0, "desc")
            row = listed[0]
            self.assertEqual(row.cover_path, f"/library/resources/{rid}/content")
            self.assertNotEqual(row.thumbnail_path, row.cover_path)
            self.assertIn(f"/library/resources/{rid}/files/", row.thumbnail_path or "")
            self.assertIn("/content", row.thumbnail_path or "")
            detail = await ResourceRepository(session).get(rid)
            assert detail is not None
            self.assertEqual(detail.thumbnail_path, row.thumbnail_path)

    async def test_replace_cover_overwrites_same_thumb(self) -> None:
        src = self._png("d.png", color=(10, 200, 10))
        cover = self._png("cover.png", size=(80, 80), color=(10, 10, 200))
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, src)
            dest = self._thumb_path("image", rid)
            before = dest.read_bytes()
            svc = LibraryQueryService(
                ResourceRepository(session),
                TaskSummaryRepository(session),
                file_ops=self.ops,
                store_root=self.store,
            )
            after = await svc.replace_cover(rid, CoverReplace(path=str(cover)))
            assert after is not None
            thumbs = [f for f in after.files if f.role == FILE_ROLE_THUMBNAIL]
            self.assertEqual(len(thumbs), 1)
            self.assertEqual(Path(thumbs[0].path).name, THUMB_GRID_NAME)
            self.assertTrue(dest.is_file())
            self.assertNotEqual(dest.read_bytes(), before)
            self.assertNotIn("thumbs/grid", after.cover_path or "")


if __name__ == "__main__":
    unittest.main()
