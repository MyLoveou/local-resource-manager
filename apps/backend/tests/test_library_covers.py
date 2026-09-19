"""封面治理：手指定、锁定、导入海报/抽帧/图标。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.covers import (
    COVER_ORIGIN_USER,
    CoverNotAllowedError,
    apply_ingest_cover,
    is_user_locked,
)
from app.library.application.import_service import ImportService
from app.library.application.packages import layout_for
from app.library.application.packages.resource_package import ResourcePackage
from app.library.application.schemas import CoverReplace
from app.library.application.use_cases import LibraryQueryService
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository, TaskSummaryRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.shared.models import ResourceType

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a4944415478da63000100000500010d0a2db40000000049454e44ae426082"
)


class LibraryCoversTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_image_cover_forbidden(self) -> None:
        src = self._png("a.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="i1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.IMAGE, "file", [str(src)]
            )
            rid = (await repo.list(ResourceType.IMAGE, None, 10, 0, "desc"))[0].id
            svc = LibraryQueryService(repo, TaskSummaryRepository(session), store_root=self.store)
            with self.assertRaises(CoverNotAllowedError):
                await svc.replace_cover(rid, CoverReplace(path=str(self._png("b.png"))))

    async def test_audio_replace_cover_sets_user(self) -> None:
        src = self.root / "a.mp3"
        src.write_bytes(b"ID3fake")
        poster = self._png("p.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="a1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.AUDIO, "file", [str(src)]
            )
            rid = (await repo.list(ResourceType.AUDIO, None, 10, 0, "desc"))[0].id
            svc = LibraryQueryService(repo, TaskSummaryRepository(session), store_root=self.store)
            row = await svc.replace_cover(rid, CoverReplace(path=str(poster)))
            assert row is not None
            self.assertEqual((row.extra or {}).get("coverOrigin"), COVER_ORIGIN_USER)
            self.assertTrue(any(f.role == "cover" for f in row.files or []))
            self.assertTrue(is_user_locked(row))

    async def test_audio_without_art_has_no_cover(self) -> None:
        src = self.root / "bare.mp3"
        src.write_bytes(b"ID3fake")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="a0")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.AUDIO, "file", [str(src)]
            )
            self.assertEqual(job.imported, 1)
            detail = await repo.get((await repo.list(ResourceType.AUDIO, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertFalse(any(f.role == "cover" for f in detail.files or []))
            self.assertNotEqual((detail.extra or {}).get("coverOrigin"), "embedded")

    async def test_audio_embedded_mocked(self) -> None:
        src = self.root / "song.mp3"
        src.write_bytes(b"ID3fake")
        art = self._png("art.png")

        def fake_art(_src: Path, dest: Path) -> bool:
            dest.write_bytes(art.read_bytes())
            return True

        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="a2")
            with patch("app.library.application.covers.ingest.extract_audio_cover", fake_art):
                await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                    job, ResourceType.AUDIO, "file", [str(src)]
                )
            self.assertEqual(job.imported, 1)
            detail = await repo.get((await repo.list(ResourceType.AUDIO, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "embedded")
            self.assertIn("/files/", detail.cover_path or "")
            self.assertTrue(any(f.role == "cover" for f in detail.files or []))

    async def test_user_lock_skips_auto(self) -> None:
        src = self.root / "a.mp3"
        src.write_bytes(b"ID3")
        poster = self._png("p.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="a1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.AUDIO, "file", [str(src)]
            )
            rid = (await repo.list(ResourceType.AUDIO, None, 10, 0, "desc"))[0].id
            svc = LibraryQueryService(repo, TaskSummaryRepository(session), store_root=self.store)
            await svc.replace_cover(rid, CoverReplace(path=str(poster)))
            row = await repo.get(rid)
            assert row is not None
            layout = layout_for(ResourceType.AUDIO)
            assert layout is not None
            package = ResourcePackage(
                self.store,
                ResourceType.AUDIO,
                rid,
                self.ops,
                cover_falls_back_to_primary=layout.cover_falls_back_to_primary,
            )
            before = Path(next(f.path for f in row.files or [] if f.role == "cover")).read_bytes()
            await apply_ingest_cover(
                repo, row, package, ResourceType.AUDIO, role_paths={}, source_root=self.root
            )
            after = Path(next(f.path for f in (await repo.get(rid)).files or [] if f.role == "cover")).read_bytes()
            self.assertEqual(before, after)
            self.assertEqual(((await repo.get(rid)).extra or {}).get("coverOrigin"), COVER_ORIGIN_USER)

    async def test_game_folder_poster(self) -> None:
        folder = self.root / "G"
        folder.mkdir()
        (folder / "G.exe").write_bytes(b"MZ")
        self._png("G/cover.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="g1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.GAME, "directory", [str(folder)]
            )
            detail = await repo.get((await repo.list(ResourceType.GAME, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "folder")
            self.assertTrue(any(f.role == "cover" for f in detail.files or []))
            self.assertTrue(any(f.role == "thumbnail" for f in detail.files or []))

    async def test_video_frame_mocked(self) -> None:
        video = self.root / "v.mp4"
        video.write_bytes(b"not-a-real-video")
        frame = self._png("frame.jpg")

        def fake_frame(src: Path, dest: Path, *, duration=None) -> bool:
            dest.write_bytes(frame.read_bytes())
            return True

        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="v1")
            with patch("app.library.application.covers.ingest.extract_video_frame", fake_frame):
                await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                    job, ResourceType.VIDEO, "file", [str(video)]
                )
            self.assertEqual(job.imported, 1)
            detail = await repo.get((await repo.list(ResourceType.VIDEO, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "frame")
            self.assertIn("/files/", detail.cover_path or "")

    async def test_series_poster_not_frame(self) -> None:
        folder = self.root / "Show"
        folder.mkdir()
        (folder / "Show - S01E01.mp4").write_bytes(b"vid")
        self._png("Show/poster.jpg")

        def boom(*_a, **_k) -> bool:
            raise AssertionError("should not extract frame")

        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="s1")
            with patch("app.library.application.covers.ingest.extract_video_frame", boom):
                await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                    job, ResourceType.ANIME, "directory", [str(folder)]
                )
            self.assertEqual(job.imported, 1)
            detail = await repo.get((await repo.list(ResourceType.ANIME, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "folder")

    async def test_game_exe_icon_mocked(self) -> None:
        folder = self.root / "IconGame"
        folder.mkdir()
        (folder / "IconGame.exe").write_bytes(b"MZ")
        icon = self._png("icon.png")

        def fake_icon(src: Path, dest: Path) -> bool:
            dest.write_bytes(icon.read_bytes())
            return True

        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="g2")
            with patch("app.library.application.covers.ingest.extract_exe_icon", fake_icon):
                await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                    job, ResourceType.GAME, "directory", [str(folder)]
                )
            detail = await repo.get((await repo.list(ResourceType.GAME, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "exe")

    def test_ffmpeg_temp_uses_jpg_suffix(self) -> None:
        import subprocess

        from app.library.application.covers.frame import extract_video_frame

        dest = self.root / "out.jpg"
        with patch("app.library.application.covers.frame.shutil.which", return_value="ffmpeg"):
            with patch("app.library.application.covers.frame.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"bad")
                self.assertFalse(extract_video_frame(self.root / "a.mp4", dest, duration=2))
        out = Path(run.call_args.args[0][-1])
        self.assertEqual(out.suffix.lower(), ".jpg")
        self.assertNotEqual(out.suffix.lower(), ".tmp")

    def test_extract_frame_with_ffmpeg_if_present(self) -> None:
        import shutil
        import subprocess

        from app.library.application.covers.frame import extract_video_frame
        from app.shared.media_types import FFMPEG_BIN

        binary = shutil.which(FFMPEG_BIN)
        if binary is None:
            self.skipTest("ffmpeg not on PATH")
        src = self.root / "clip.mp4"
        completed = subprocess.run(
            [
                binary,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=64x36:d=2",
                str(src),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if completed.returncode != 0 or not src.is_file():
            self.skipTest("could not synthesize test mp4")
        dest = self.root / "frame.jpg"
        self.assertTrue(extract_video_frame(src, dest, duration=2))
        self.assertTrue(dest.is_file())
        self.assertGreater(dest.stat().st_size, 0)

    def test_audio_cover_temp_uses_jpg_suffix(self) -> None:
        import subprocess

        from app.library.application.covers.embedded import extract_audio_cover

        dest = self.root / "out.jpg"
        with patch("app.library.application.covers.embedded.shutil.which", return_value="ffmpeg"):
            with patch("app.library.application.covers.embedded.subprocess.run") as run:
                run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"bad")
                self.assertFalse(extract_audio_cover(self.root / "a.mp3", dest))
        out = Path(run.call_args.args[0][-1])
        self.assertEqual(out.suffix.lower(), ".jpg")

    def test_extract_audio_cover_with_ffmpeg_if_present(self) -> None:
        import shutil
        import subprocess

        from PIL import Image

        from app.library.application.covers.embedded import extract_audio_cover
        from app.shared.media_types import FFMPEG_BIN

        binary = shutil.which(FFMPEG_BIN)
        if binary is None:
            self.skipTest("ffmpeg not on PATH")
        jpg = self.root / "art.jpg"
        Image.new("RGB", (32, 32), (20, 80, 40)).save(jpg, "JPEG")
        bare = self.root / "bare.mp3"
        muxed = self.root / "song.mp3"
        make_audio = subprocess.run(
            [binary, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-q:a", "9", str(bare)],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if make_audio.returncode != 0 or not bare.is_file():
            self.skipTest("could not synthesize test mp3")
        mux = subprocess.run(
            [
                binary,
                "-y",
                "-i",
                str(bare),
                "-i",
                str(jpg),
                "-map",
                "0:a",
                "-map",
                "1:v",
                "-c",
                "copy",
                "-disposition:v",
                "attached_pic",
                str(muxed),
            ],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if mux.returncode != 0 or not muxed.is_file():
            self.skipTest("could not mux attached picture")
        dest = self.root / "embedded.jpg"
        self.assertTrue(extract_audio_cover(muxed, dest))
        self.assertTrue(dest.is_file())
        self.assertGreater(dest.stat().st_size, 0)


def _epub_bytes(*, with_opf_cover: bool, extra_chapter: bool) -> bytes:
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        cover_item = (
            '<item id="cov" href="cover.png" media-type="image/png" properties="cover-image"/>'
            if with_opf_cover
            else ""
        )
        archive.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bid" version="3.0">
  <manifest>
    {cover_item}
    <item id="ch" href="chapter.png" media-type="image/png"/>
  </manifest>
</package>
""",
        )
        if with_opf_cover:
            archive.writestr("OEBPS/cover.png", _PNG)
        if extra_chapter or not with_opf_cover:
            archive.writestr("OEBPS/chapter.png", _PNG)
    return buf.getvalue()


class LibraryCoversCompleteTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_epub_sidecar_beats_embedded(self) -> None:
        epub = self.root / "book.epub"
        epub.write_bytes(_epub_bytes(with_opf_cover=True, extra_chapter=True))
        self._png("cover.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="n1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.NOVEL, "file", [str(epub)]
            )
            detail = await repo.get((await repo.list(ResourceType.NOVEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "folder")

    async def test_epub_opf_cover(self) -> None:
        epub = self.root / "only.epub"
        epub.write_bytes(_epub_bytes(with_opf_cover=True, extra_chapter=True))
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="n2")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.NOVEL, "file", [str(epub)]
            )
            detail = await repo.get((await repo.list(ResourceType.NOVEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "embedded")
            self.assertTrue(any(f.role == "cover" for f in detail.files or []))

    async def test_epub_chapter_image_not_cover(self) -> None:
        epub = self.root / "plain.epub"
        epub.write_bytes(_epub_bytes(with_opf_cover=False, extra_chapter=True))
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="n3")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.NOVEL, "file", [str(epub)]
            )
            detail = await repo.get((await repo.list(ResourceType.NOVEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertFalse(any(f.role == "cover" for f in detail.files or []))

    async def test_pdf_first_page(self) -> None:
        from app.library.application.covers.pdf_page import render_pdf_first_page

        pdf = self.root / "a.pdf"
        pdf.write_bytes(_minimal_pdf())
        dest = self.root / "p.jpg"
        if not render_pdf_first_page(pdf, dest):
            self.skipTest("pypdfium2 could not render fixture pdf")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="n4")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.NOVEL, "file", [str(pdf)]
            )
            detail = await repo.get((await repo.list(ResourceType.NOVEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "page")
            self.assertTrue(any(f.role == "thumbnail" for f in detail.files or []))

    async def test_bad_pdf_imports(self) -> None:
        pdf = self.root / "bad.pdf"
        pdf.write_bytes(b"not-a-pdf")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="n5")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.NOVEL, "file", [str(pdf)]
            )
            self.assertEqual(job.imported, 1)
            detail = await repo.get((await repo.list(ResourceType.NOVEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertFalse(any(f.role == "cover" for f in detail.files or []))

    async def test_model_same_stem_png(self) -> None:
        glb = self.root / "foo.glb"
        glb.write_bytes(b"glTF")
        self._png("foo.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="m1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.MODEL, "file", [str(glb)]
            )
            detail = await repo.get((await repo.list(ResourceType.MODEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "folder")

    async def test_poster_beats_same_stem(self) -> None:
        glb = self.root / "foo.glb"
        glb.write_bytes(b"glTF")
        self._png("foo.png")
        self._png("cover.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="m2")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.MODEL, "file", [str(glb)]
            )
            detail = await repo.get((await repo.list(ResourceType.MODEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "folder")
            cover = next(f for f in detail.files or [] if f.role == "cover")
            from PIL import Image

            with Image.open(cover.path) as image:
                self.assertEqual(image.size[0], 1)

    async def test_comic_dir_page_cover(self) -> None:
        folder = self.root / "C"
        folder.mkdir()
        self._png("C/01.png")
        self._png("C/02.png")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="c1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.COMIC, "directory", [str(folder)]
            )
            detail = await repo.get((await repo.list(ResourceType.COMIC, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "page")
            self.assertIn("/files/", detail.cover_path or "")

    async def test_cbz_first_image(self) -> None:
        import io
        import zipfile

        from PIL import Image

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("page-10.png", _PNG)
            bigger = self.root / "big.png"
            Image.new("RGB", (2, 2), (255, 0, 0)).save(bigger, "PNG")
            archive.writestr("page-2.png", bigger.read_bytes())
        cbz = self.root / "book.cbz"
        cbz.write_bytes(buf.getvalue())
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="c2")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.COMIC, "file", [str(cbz)]
            )
            detail = await repo.get((await repo.list(ResourceType.COMIC, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertEqual((detail.extra or {}).get("coverOrigin"), "page")
            cover = next(f for f in detail.files or [] if f.role == "cover")
            with Image.open(cover.path) as image:
                self.assertEqual(image.size, (2, 2))

    async def test_cbr_no_auto_cover(self) -> None:
        cbr = self.root / "book.cbr"
        cbr.write_bytes(b"Rar!")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="c3")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.COMIC, "file", [str(cbr)]
            )
            self.assertEqual(job.imported, 1)
            rows = await repo.list(ResourceType.COMIC, None, 10, 0, "desc")
            self.assertEqual(len(rows), 1)
            detail = await repo.get(rows[0].id)
            assert detail is not None
            self.assertFalse(any(f.role == "cover" for f in detail.files or []))

    async def test_txt_no_cover(self) -> None:
        txt = self.root / "n.txt"
        txt.write_text("hi", encoding="utf-8")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="n6")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.NOVEL, "file", [str(txt)]
            )
            self.assertEqual(job.imported, 1)
            detail = await repo.get((await repo.list(ResourceType.NOVEL, None, 10, 0, "desc"))[0].id)
            assert detail is not None
            self.assertFalse(any(f.role == "cover" for f in detail.files or []))


def _minimal_pdf() -> bytes:
    return (
        b"%PDF-1.1\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 72 72]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
    )


if __name__ == "__main__":
    unittest.main()
