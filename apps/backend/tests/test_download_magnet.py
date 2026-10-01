"""磁力链接校验，以及 aria2 完成后复制进视频库。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.download.application.aria2 import Aria2Snapshot, parse_status, pull_magnet
from app.download.application.engine import DownloadAbort
from app.download.application.errors import DownloadError
from app.download.application.magnet import validate_magnet
from app.download.application.service import create_task, run_task
from app.download.domain.models import DownloadStatus
from app.download.infrastructure.repo import DownloadRepository
from app.library.application.media_probe import ProbeFields
from app.library.infrastructure.repositories import ResourceRepository
from app.download.domain.models import (
    DownloadEngine,
    Protocol,
)
from app.shared.db.migrations import migrate
from app.library.domain.models import ResourceType

_HASH = "0123456789abcdef0123456789abcdef01234567"


def _magnet(dn: str = "clip.mp4") -> str:
    return f"magnet:?xt=urn:btih:{_HASH}&dn={dn}"


class MagnetParseTests(unittest.TestCase):
    def test_accepts_btih_and_name(self) -> None:
        link = validate_magnet(_magnet())
        self.assertIn(f"xt=urn:btih:{_HASH}", link.canonical)
        self.assertEqual(link.display_name, "clip.mp4")

    def test_rejects_direct_params_private_tracker_and_bad_hash(self) -> None:
        with self.assertRaises(DownloadError):
            validate_magnet(f"magnet:?xt=urn:btih:{_HASH}&ws=http://127.0.0.1/a.mp4")
        with self.assertRaises(DownloadError):
            validate_magnet(f"magnet:?xt=urn:btih:{_HASH}&tr=http://127.0.0.1/announce")
        with self.assertRaises(DownloadError):
            validate_magnet("magnet:?xt=urn:btih:zz")


class Aria2StatusTests(unittest.TestCase):
    def test_zero_total_is_unknown(self) -> None:
        snap = parse_status(
            {
                "status": "active",
                "totalLength": "0",
                "completedLength": "4",
                "downloadSpeed": "8",
                "files": [{"path": "clip.mp4"}],
            }
        )
        self.assertIsNone(snap.total)
        self.assertEqual(snap.completed, 4)
        self.assertEqual(snap.files, [Path("clip.mp4")])


class _FakeAria2:
    def __init__(self, directory_file: str, payload: bytes, status: str = "complete") -> None:
        self.directory_file = directory_file
        self.payload = payload
        self.status = status
        self.directory = Path(".")
        self.paused: str | None = None

    async def add_uri(self, uri: str, directory: Path) -> str:
        self.directory = Path(directory)
        return "gid-1"

    async def unpause(self, gid: str) -> None:
        return None

    async def tell(self, gid: str) -> Aria2Snapshot:
        path = self.directory / self.directory_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.payload)
        return Aria2Snapshot(self.status, len(self.payload), len(self.payload), 0, None, [path])

    async def pause(self, gid: str) -> None:
        self.paused = gid

    async def remove(self, gid: str) -> None:
        return None


class MagnetDownloadTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_missing_aria2_does_not_create(self) -> None:
        async with self.factory() as session:
            with patch("app.download.application.service.find_aria2c", return_value=None):
                with self.assertRaises(DownloadError) as ctx:
                    await create_task(session, _magnet(), self.db_path)
            self.assertIn("aria2", str(ctx.exception))
            self.assertEqual(await DownloadRepository(session).list_all(), [])

    async def test_create_uses_aria2(self) -> None:
        async with self.factory() as session:
            with patch("app.download.application.service.find_aria2c", return_value=Path("aria2c")):
                task = await create_task(session, _magnet(), self.db_path)
        self.assertEqual(task.protocol, Protocol.MAGNET)
        self.assertEqual(task.engine, DownloadEngine.ARIA2)
        self.assertEqual(task.filename, "clip.mp4")
        self.assertTrue(task.save_path is not None and task.save_path.endswith(str(task.id)))

    async def test_complete_ingests_video(self) -> None:
        payload = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
        fake = _FakeAria2("clip.mp4", payload)
        async with self.factory() as session:
            with patch("app.download.application.service.find_aria2c", return_value=Path("aria2c")):
                task = await create_task(session, _magnet(), self.db_path)
        with (
            patch("app.library.application.import_service.probe_media", return_value=ProbeFields()),
            patch("app.library.application.import_service.apply_ingest_cover", new=AsyncMock()),
            patch("app.scrape.application.enqueue.enqueue_search_after_import", new=AsyncMock()),
        ):
            await run_task(self.factory, task.id, self.db_path, aria2=fake)
        async with self.factory() as session:
            done = await DownloadRepository(session).get(task.id)
            assert done is not None
            self.assertEqual(done.status, DownloadStatus.DONE)
            assert done.target_resource_id is not None
            resource = await ResourceRepository(session).get(done.target_resource_id)
            assert resource is not None
            self.assertEqual(resource.type, ResourceType.VIDEO)

    async def test_without_video_fails(self) -> None:
        fake = _FakeAria2("readme.txt", b"nope")
        async with self.factory() as session:
            with patch("app.download.application.service.find_aria2c", return_value=Path("aria2c")):
                task = await create_task(session, _magnet("readme"), self.db_path)
        await run_task(self.factory, task.id, self.db_path, aria2=fake)
        async with self.factory() as session:
            done = await DownloadRepository(session).get(task.id)
            assert done is not None
            self.assertEqual(done.status, DownloadStatus.FAILED)
            self.assertEqual(done.error, "没有可入库的视频")

    async def test_pause_keeps_gid(self) -> None:
        fake = _FakeAria2("clip.mp4", b"x", status="active")

        async def abort() -> str:
            return "paused"

        with self.assertRaises(DownloadAbort) as ctx:
            await pull_magnet(_magnet(), self.root / "stage", should_abort=abort, client=fake)
        self.assertEqual(ctx.exception.reason, "paused")
        self.assertEqual(ctx.exception.gid, "gid-1")
        self.assertEqual(fake.paused, "gid-1")
