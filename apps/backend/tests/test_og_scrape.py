"""图片刮削：页面链接的 Open Graph，拒绝内网。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.shared.errors import DownloadError
from app.library.infrastructure.repositories import ResourceRepository
from app.scrape.application.images import public_image_url, unique_https
from app.scrape.application.jobs import ScrapeError, create_or_reuse_job, run_search
from app.scrape.application.providers.base import MetadataProvider, SearchHit
from app.scrape.application.providers.og import OgProvider, page_url_or_error, parse_open_graph
from app.shared.db.migrations import migrate
from app.library.domain.models import (
    Resource,
    ResourceStatus,
    ResourceType,
)

_HTML = """
<html><head>
<meta property="og:title" content="海边日落">
<meta property="og:image" content="https://image.tmdb.org/t/p/w500/poster.jpg">
<meta property="og:description" content="一句简介">
<title>忽略</title>
</head></html>
"""


class _Resp:
    def __init__(self, *, status: int = 200, headers: dict | None = None, text: str = "", url: str = "") -> None:
        self.status_code = status
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.text = text
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(str(self.status_code))


class _Client:
    def __init__(self, resp: _Resp) -> None:
        self.resp = resp
        self.urls: list[str] = []

    async def get(self, url: str) -> _Resp:
        self.urls.append(url)
        return self.resp

    async def aclose(self) -> None:
        return None


class _Capture(MetadataProvider):
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search(self, query: str) -> list[SearchHit]:
        self.queries.append(query)
        return [SearchHit(title="海边日落", key=f"og:{query}", source="og")]

    async def detail(self, key: str) -> SearchHit:
        raise AssertionError(key)


class OgParseTests(unittest.TestCase):
    def test_parse_title_image_description(self) -> None:
        title, image, desc = parse_open_graph(_HTML, "https://example.com/art")
        self.assertEqual(title, "海边日落")
        self.assertEqual(image, "https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertEqual(desc, "一句简介")

    def test_private_page_rejected(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            page_url_or_error("http://127.0.0.1/secret")
        self.assertIn("本机", str(ctx.exception))

    def test_public_image_keeps_allowlist_and_drops_loopback(self) -> None:
        kept = public_image_url("https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertEqual(kept, "https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertIsNone(public_image_url("https://127.0.0.1/a.jpg"))
        self.assertEqual(
            unique_https(
                [
                    "https://image.tmdb.org/t/p/w500/poster.jpg",
                    "http://127.0.0.1/a.jpg",
                ]
            ),
            ["https://image.tmdb.org/t/p/w500/poster.jpg"],
        )


class OgProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_reads_open_graph(self) -> None:
        client = _Client(_Resp(text=_HTML, url="https://example.com/art"))
        with patch(
            "app.scrape.application.providers.og.validate_http_url",
            side_effect=lambda raw: raw,
        ):
            hits = await OgProvider(client).search("https://example.com/art")
        self.assertEqual(hits[0].title, "海边日落")
        self.assertEqual(hits[0].key, "og:https://example.com/art")
        self.assertEqual(hits[0].thumbnail_url, "https://image.tmdb.org/t/p/w500/poster.jpg")

    async def test_redirect_to_loopback_rejected(self) -> None:
        client = _Client(
            _Resp(status=302, headers={"location": "http://127.0.0.1/hidden"}, text="")
        )

        def _validate(raw: str) -> str:
            if "127.0.0.1" in raw:
                raise DownloadError("不允许下载内网或本机地址", 400)
            return raw

        with patch("app.scrape.application.providers.og.validate_http_url", side_effect=_validate):
            with self.assertRaises(RuntimeError):
                await OgProvider(client).search("https://example.com/art")


class OgJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "t.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path.as_posix()}")
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def test_image_requires_page_url_and_searches_it(self) -> None:
        async with self.factory() as session:
            img = await ResourceRepository(session).create(
                Resource(type=ResourceType.IMAGE, title="a.png", status=ResourceStatus.ACTIVE)
            )
            with self.assertRaises(ScrapeError) as missing:
                await create_or_reuse_job(session, img.id)
            self.assertEqual(str(missing.exception), "请填写页面链接")
            with self.assertRaises(ScrapeError):
                await create_or_reuse_job(session, img.id, query="http://127.0.0.1/x")
            with patch("app.scrape.application.jobs.page_url_or_error", side_effect=lambda raw: raw):
                job = await create_or_reuse_job(session, img.id, query="https://example.com/art")
            capture = _Capture()
            with patch("app.scrape.application.jobs.providers_for", return_value=[capture]):
                await run_search(session, job.id)
            self.assertEqual(capture.queries, ["https://example.com/art"])
