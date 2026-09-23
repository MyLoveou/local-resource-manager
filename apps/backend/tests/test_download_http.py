"""HTTP 直链下载：SSRF、任务状态、mock 入库。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.download.application.errors import DownloadError
from app.download.application.service import (
    cancel_task,
    create_task,
    pause_task,
    resume_task,
    run_task,
)
from app.download.application.ssrf import validate_http_url
from app.download.domain.models import DownloadStatus, DownloadTask
from app.download.infrastructure.repo import DownloadRepository
from app.library.application.media_probe import ProbeFields
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.db.migrations import migrate
from app.shared.models import Resource, ResourceStatus, ResourceType


class SsrfTests(unittest.TestCase):
    def test_rejects_magnet_file_and_loopback(self) -> None:
        with self.assertRaises(DownloadError):
            validate_http_url("magnet:?xt=urn:btih:abc")
        with self.assertRaises(DownloadError):
            validate_http_url("file:///c:/a.mp4")
        with self.assertRaises(DownloadError):
            validate_http_url("http://127.0.0.1/x.mp4")


class DownloadHttpTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_invalid_url_rejected(self) -> None:
        async with self.factory() as session:
            with self.assertRaises(DownloadError) as ctx:
                await create_task(session, "http://127.0.0.1/clip.mp4", self.db_path)
            self.assertEqual(ctx.exception.status_code, 400)
            jobs = await DownloadRepository(session).list_all()
            self.assertEqual(jobs, [])

    async def test_pause_only_running(self) -> None:
        async with self.factory() as session:
            with patch("app.download.application.service.validate_http_url", side_effect=lambda u: u):
                created = await create_task(session, "http://files.test/clip.mp4", self.db_path)
            with self.assertRaises(DownloadError):
                await pause_task(session, created.id)
            repo = DownloadRepository(session)
            row = await repo.get(created.id)
            assert row is not None
            row.start()
            await repo.save(row)
            paused = await pause_task(session, created.id)
            self.assertEqual(paused.status, DownloadStatus.PAUSED)
            queued = await resume_task(session, created.id)
            self.assertEqual(queued.status, DownloadStatus.QUEUED)

    async def test_download_ingests_video(self) -> None:
        payload = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=payload,
                headers={"Content-Type": "video/mp4", "Content-Disposition": 'attachment; filename="clip.mp4"'},
            )

        transport = httpx.MockTransport(handler)
        async with self.factory() as session:
            with patch("app.download.application.service.validate_http_url", side_effect=lambda u: u):
                task = await create_task(session, "http://files.test/clip.mp4", self.db_path)
        async with httpx.AsyncClient(transport=transport) as client:
            with (
                patch("app.download.application.engine.validate_http_url", side_effect=lambda u: u),
                patch("app.library.application.import_service.probe_media", return_value=ProbeFields()),
                patch("app.library.application.import_service.apply_ingest_cover", new=AsyncMock()),
                patch("app.scrape.application.enqueue.enqueue_search_after_import", new=AsyncMock()),
            ):
                await run_task(self.factory, task.id, self.db_path, client=client)
        async with self.factory() as session:
            done = await DownloadRepository(session).get(task.id)
            assert done is not None
            self.assertEqual(done.status, DownloadStatus.DONE)
            self.assertIsNotNone(done.target_resource_id)
            resource = await ResourceRepository(session).get(done.target_resource_id)
            assert resource is not None
            self.assertEqual(resource.type, ResourceType.VIDEO)

    async def test_duplicate_links_existing(self) -> None:
        payload = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
        sample = self.root / "exist.mp4"
        sample.write_bytes(payload)
        async with self.factory() as session:
            repo = ResourceRepository(session)
            created = await repo.create(
                Resource(type=ResourceType.VIDEO, title="exist", status=ResourceStatus.ACTIVE)
            )
            from app.library.application.import_service import hash_file

            digest, size = hash_file(sample)
            await repo.add_file(
                created.id,
                path=str(sample),
                sha256=digest,
                size=size,
                format_="mp4",
                role="primary",
            )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=payload, headers={"Content-Type": "video/mp4"})

        transport = httpx.MockTransport(handler)
        async with self.factory() as session:
            with patch("app.download.application.service.validate_http_url", side_effect=lambda u: u):
                task = await create_task(session, "http://files.test/exist.mp4", self.db_path)
        async with httpx.AsyncClient(transport=transport) as client:
            with (
                patch("app.download.application.engine.validate_http_url", side_effect=lambda u: u),
                patch("app.library.application.import_service.probe_media", return_value=ProbeFields()),
                patch("app.library.application.import_service.apply_ingest_cover", new=AsyncMock()),
                patch("app.scrape.application.enqueue.enqueue_search_after_import", new=AsyncMock()),
            ):
                await run_task(self.factory, task.id, self.db_path, client=client)
        async with self.factory() as session:
            done = await DownloadRepository(session).get(task.id)
            assert done is not None
            self.assertEqual(done.status, DownloadStatus.DONE)
            self.assertEqual(done.target_resource_id, created.id)

    async def test_cancel_queued(self) -> None:
        async with self.factory() as session:
            with patch("app.download.application.service.validate_http_url", side_effect=lambda u: u):
                task = await create_task(session, "http://files.test/clip.mp4", self.db_path)
            cancelled = await cancel_task(session, task.id)
            self.assertEqual(cancelled.status, DownloadStatus.FAILED)
            self.assertEqual(cancelled.error, "已取消")
