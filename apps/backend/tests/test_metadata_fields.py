"""元数据字段：探测、待办立刻写、多语言字幕、展示档位。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.import_service import ImportService
from app.library.application.media_probe import ProbeFields, probe_video
from app.library.application.schemas import ResourcePatch, SubtitleAdd, TodoCreate, TodoPatch
from app.library.application.subtitle_naming import language_tag, subtitle_dest_name
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.library.domain.media_labels import (
    clarity_label,
    quality_label,
)
from app.library.domain.models import ResourceType

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class MetadataFieldsTests(unittest.IsolatedAsyncioTestCase):
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

    def _file(self, name: str, data: bytes = b"x") -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _svc(self, session) -> LibraryQueryService:
        return LibraryQueryService(
            ResourceRepository(session),
            TaskSummaryRepository(session),
            file_ops=self.ops,
            store_root=self.store,
        )

    async def _import(
        self,
        session,
        type_: ResourceType,
        source: Path,
        probe=None,
    ) -> int:
        repo = ResourceRepository(session)
        job = ImportJobState(id="j1")
        kwargs = {}
        if probe is not None:
            kwargs["probe"] = probe
        await ImportService(repo, store_root=self.store, file_ops=self.ops, **kwargs).run(
            job, type_, "file", [str(source)]
        )
        self.assertEqual(job.imported, 1)
        items = await repo.list(type_, None, 10, 0, "desc")
        assert items[0].id is not None
        return items[0].id

    async def test_detail_has_author_todos_format(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            self.assertIsNone(got.author)
            self.assertEqual(got.todos, [])
            primary = next(f for f in got.files if f.role == "primary")
            self.assertEqual(primary.format, "png")

    async def test_import_image_has_size(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            primary = next(f for f in got.files if f.role == "primary")
            self.assertEqual(primary.width, 1)
            self.assertEqual(primary.height, 1)

    async def test_import_video_without_ffprobe(self) -> None:
        async with self.factory() as session:
            rid = await self._import(
                session,
                ResourceType.VIDEO,
                self._file("电影.mp4"),
                probe=lambda _t, _p: ProbeFields(),
            )
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            primary = next(f for f in got.files if f.role == "primary")
            self.assertIsNone(primary.width)
            self.assertIsNone(primary.bitrate)

    async def test_probe_video_missing_binary(self) -> None:
        with patch("app.library.application.media_probe.shutil.which", return_value=None):
            fields = probe_video(self._file("x.mp4"))
        self.assertIsNone(fields.width)

    async def test_todo_writes_immediately(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            svc = self._svc(session)
            after = await svc.add_todo(rid, TodoCreate(content="补封面"))
            assert after is not None
            self.assertEqual(len(after.todos), 1)
            self.assertEqual(after.todos[0].content, "补封面")
            self.assertFalse(after.todos[0].done)
            todo_id = after.todos[0].id
            assert todo_id is not None
            checked = await svc.patch_todo(rid, todo_id, TodoPatch(done=True))
            assert checked is not None
            self.assertTrue(checked.todos[0].done)
            gone = await svc.delete_todo(rid, todo_id)
            assert gone is not None
            self.assertEqual(gone.todos, [])

    async def test_patch_author(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            updated = await self._svc(session).patch(rid, ResourcePatch(author="Alice"))
            assert updated is not None
            self.assertEqual(updated.author, "Alice")

    async def test_subtitle_uses_original_stem_and_lang(self) -> None:
        async with self.factory() as session:
            rid = await self._import(
                session,
                ResourceType.VIDEO,
                self._file("电影.mp4"),
                probe=lambda _t, _p: ProbeFields(),
            )
            src = self._file("foo.zh.srt", b"1")
            after = await self._svc(session).add_subtitle(rid, SubtitleAdd(path=str(src)))
            assert after is not None
            subs = [f for f in after.files if f.role == "subtitle"]
            self.assertEqual(len(subs), 1)
            self.assertTrue(subs[0].path.endswith("电影.zh.srt"))
            self.assertTrue(Path(subs[0].path).is_file())
            self.assertTrue(src.is_file())

    async def test_subtitle_multi_lang(self) -> None:
        async with self.factory() as session:
            rid = await self._import(
                session,
                ResourceType.VIDEO,
                self._file("电影.mp4"),
                probe=lambda _t, _p: ProbeFields(),
            )
            svc = self._svc(session)
            await svc.add_subtitle(rid, SubtitleAdd(path=str(self._file("foo.zh.srt", b"zh"))))
            after = await svc.add_subtitle(rid, SubtitleAdd(path=str(self._file("bar.en.srt", b"en"))))
            assert after is not None
            names = sorted(Path(f.path).name for f in after.files if f.role == "subtitle")
            self.assertEqual(names, ["电影.en.srt", "电影.zh.srt"])

    async def test_subtitle_rejected_for_image(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            with self.assertRaises(ValueError):
                await self._svc(session).add_subtitle(
                    rid, SubtitleAdd(path=str(self._file("a.srt", b"1")))
                )

    def test_clarity_portrait(self) -> None:
        self.assertEqual(clarity_label(1920, 1080), "1080p")
        self.assertEqual(clarity_label(1080, 1920), "1080p")
        self.assertEqual(clarity_label(3840, 2160), "4K")
        self.assertIsNone(clarity_label(1920, None))

    def test_quality_bpp(self) -> None:
        self.assertIsNone(quality_label(1920, 1080, 30, None))
        self.assertEqual(quality_label(1920, 1080, 30, 8_000_000), "中")
        self.assertEqual(quality_label(1920, 1080, 30, 8_000_000, "hevc"), "高")

    def test_subtitle_naming(self) -> None:
        self.assertEqual(language_tag("foo.zh.srt"), "zh")
        self.assertIsNone(language_tag("电影.2020.srt"))
        self.assertEqual(subtitle_dest_name("电影", "foo.zh.srt"), "电影.zh.srt")
        self.assertEqual(subtitle_dest_name("电影", "plain.srt"), "电影.srt")

    def _jpeg_with_taken(self, name: str, exif_dt: str) -> Path:
        from PIL import Image

        path = self.root / name
        image = Image.new("RGB", (8, 8), (12, 34, 56))
        exif = image.getexif()
        exif[306] = exif_dt
        image.save(path, format="JPEG", exif=exif)
        return path

    def test_normalize_taken_at(self) -> None:
        from app.library.application.media_probe import normalize_taken_at

        self.assertEqual(normalize_taken_at("2024:03:15 14:08:01"), "2024-03-15T14:08:01")
        self.assertEqual(normalize_taken_at("2024-03-15T14:08"), "2024-03-15T14:08:00")
        self.assertIsNone(normalize_taken_at("not-a-date"))
        self.assertIsNone(normalize_taken_at("  "))

    async def test_import_jpeg_writes_taken_at(self) -> None:
        src = self._jpeg_with_taken("cam.jpg", "2024:03:15 14:08:01")
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, src)
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            primary = next(f for f in got.files if f.role == "primary")
            self.assertEqual(primary.exif_taken_at, "2024-03-15T14:08:01")

    async def test_import_png_taken_at_empty(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            got = await ResourceRepository(session).get(rid)
            assert got is not None
            primary = next(f for f in got.files if f.role == "primary")
            self.assertIsNone(primary.exif_taken_at)

    async def test_patch_taken_at(self) -> None:
        async with self.factory() as session:
            rid = await self._import(session, ResourceType.IMAGE, self._png("a.png"))
            updated = await self._svc(session).patch(rid, ResourcePatch(exif_taken_at="2020-01-02T03:04"))
            assert updated is not None
            primary = next(f for f in updated.files if f.role == "primary")
            self.assertEqual(primary.exif_taken_at, "2020-01-02T03:04:00")
            cleared = await self._svc(session).patch(rid, ResourcePatch(exif_taken_at=""))
            assert cleared is not None
            primary = next(f for f in cleared.files if f.role == "primary")
            self.assertIsNone(primary.exif_taken_at)
            with self.assertRaises(ValueError):
                await self._svc(session).patch(rid, ResourcePatch(exif_taken_at="not-a-date"))

    async def test_patch_taken_at_rejects_video(self) -> None:
        async with self.factory() as session:
            rid = await self._import(
                session,
                ResourceType.VIDEO,
                self._file("电影.mp4"),
                probe=lambda _t, _p: ProbeFields(),
            )
            with self.assertRaises(ValueError):
                await self._svc(session).patch(rid, ResourcePatch(exif_taken_at="2020-01-02T03:04:00"))


if __name__ == "__main__":
    unittest.main()
