"""B 站刮削：解析 BV、手填校验、mock view 回填。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.infrastructure.repositories import ResourceRepository
from app.scrape.application.images import allowed_poster
from app.scrape.application.jobs import ScrapeError, create_or_reuse_job, run_search, select_candidate
from app.scrape.application.providers import providers_for
from app.scrape.application.providers.bilibili import BilibiliProvider, extract_ids
from app.scrape.application.providers.base import MetadataProvider, SearchHit
from app.scrape.application.providers.tmdb import TmdbProvider
from app.scrape.infrastructure.repo import ScrapeRepository
from app.shared.db.migrations import migrate
from app.shared.media_types import FILE_ROLE_PRIMARY
from app.shared.models import Resource, ResourceStatus, ResourceType


_BV = "BV1xx411c7mD"


def _view_payload() -> dict:
    return {
        "bvid": _BV,
        "aid": 2,
        "title": "投稿标题",
        "desc": "稿件简介",
        "pic": "http://i0.hdslb.com/bfs/archive/x.jpg",
        "tname": "日常",
        "pubdate": 1700000000,
        "owner": {"name": "测试UP"},
    }


class BilibiliParseTests(unittest.TestCase):
    def test_extract_bv_url_and_av(self) -> None:
        from_bv = extract_ids(_BV)
        from_url = extract_ids(f"https://www.bilibili.com/video/{_BV}/?spm=1")
        self.assertEqual(from_bv, [("bvid", _BV)])
        self.assertEqual(from_url[0][0], "bvid")
        self.assertEqual(from_url[0][1].upper(), _BV.upper())
        self.assertEqual(extract_ids("foo av2 bar"), [("aid", "2")])

    def test_poster_hosts(self) -> None:
        self.assertTrue(allowed_poster("https://i0.hdslb.com/bfs/archive/x.jpg"))
        self.assertFalse(allowed_poster("https://evilhdslb.com/x.jpg"))
        self.assertFalse(allowed_poster("https://cdn.evil.example/i0.hdslb.com/x.jpg"))

    def test_anime_providers_skip_bilibili(self) -> None:
        names = [type(p).__name__ for p in providers_for(ResourceType.ANIME)]
        self.assertNotIn("BilibiliProvider", names)
        video_names = [type(p).__name__ for p in providers_for(ResourceType.VIDEO)]
        self.assertIn("BilibiliProvider", video_names)


class BilibiliJobTests(unittest.IsolatedAsyncioTestCase):
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

    async def _video(self, session, title: str = "clip.mp4") -> Resource:
        repo = ResourceRepository(session)
        return await repo.create(
            Resource(type=ResourceType.VIDEO, title=title, status=ResourceStatus.ACTIVE)
        )

    async def test_name_query_searches_providers(self) -> None:
        captured: list[str] = []

        class Cap(MetadataProvider):
            async def search(self, query: str) -> list[SearchHit]:
                captured.append(query)
                return [
                    SearchHit(title=query, key="fake:1", source="fake", thumbnail_url=None, relevance=1.0)
                ]

            async def detail(self, key: str):
                raise RuntimeError("unused")

        cap = Cap()
        async with self.factory() as session:
            created = await self._video(session, title="hashname.mp4")
            job = await create_or_reuse_job(session, created.id, query="天降之物")
            self.assertEqual(job.query, "天降之物")
            with patch("app.scrape.application.jobs.providers_for", return_value=[cap]):
                await run_search(session, job.id)
        self.assertEqual(captured, ["天降之物"])

    async def test_search_select_with_mock_view(self) -> None:
        bili = BilibiliProvider()
        tmdb = TmdbProvider()

        async def fake_view(*, bvid=None, aid=None):
            return _view_payload()

        async with self.factory() as session:
            created = await self._video(session, title="unknown")
            job = await create_or_reuse_job(session, created.id, query=_BV)
            with (
                patch.object(bili, "_view", side_effect=fake_view),
                patch.object(tmdb, "search", side_effect=RuntimeError("未配置 TMDB API Key")),
                patch("app.scrape.application.jobs.providers_for", return_value=[tmdb, bili]),
                patch("app.scrape.application.jobs.provider_for_key", return_value=bili),
            ):
                await run_search(session, job.id)
                fresh = await ResourceRepository(session).get(created.id)
                self.assertEqual(fresh.title, "unknown")
                cands = await ScrapeRepository(session).list_candidates(job.id)
                self.assertEqual(len(cands), 1)
                self.assertEqual(cands[0].source, "bilibili")
                done = await ScrapeRepository(session).get_job(job.id)
                self.assertEqual(done.status.value, "done")
                await select_candidate(session, job.id, cands[0].id, apply_cover=False)
            after = await ResourceRepository(session).get(created.id)
            self.assertEqual(after.title, "投稿标题")
            self.assertEqual(after.synopsis, "稿件简介")
            self.assertEqual(after.author, "测试UP")
            self.assertEqual(after.scraped_source, f"bilibili:{_BV}")

    async def test_filename_bv_without_hand_query(self) -> None:
        bili = BilibiliProvider()

        async def fake_view(*, bvid=None, aid=None):
            return _view_payload()

        async with self.factory() as session:
            repo = ResourceRepository(session)
            created = await self._video(session, title="乱码名")
            await repo.add_file(
                created.id,
                path=str(self.root / f"{_BV}.mp4"),
                sha256=None,
                size=1,
                format_="mp4",
                role=FILE_ROLE_PRIMARY,
            )
            job = await create_or_reuse_job(session, created.id)
            with (
                patch.object(bili, "_view", side_effect=fake_view),
                patch("app.scrape.application.jobs.providers_for", return_value=[bili]),
                patch("app.scrape.application.jobs.provider_for_key", return_value=bili),
            ):
                await run_search(session, job.id)
            cands = await ScrapeRepository(session).list_candidates(job.id)
            self.assertEqual(cands[0].url, f"bilibili:{_BV}")

    async def test_short_link_stores_canonical_id(self) -> None:
        async with self.factory() as session:
            created = await self._video(session)
            with patch(
                "app.scrape.application.jobs.resolve_query_ids",
                return_value=[("bvid", _BV)],
            ):
                job = await create_or_reuse_job(session, created.id, query="https://b23.tv/abcdef")
            self.assertEqual(job.query, _BV)

    async def test_ids_do_not_fallback_to_keyword(self) -> None:
        bili = BilibiliProvider()

        async def boom(*, bvid=None, aid=None):
            raise RuntimeError("稿件不存在")

        async def should_not_keyword(keyword: str):
            raise AssertionError("不该关键词搜")

        with (
            patch.object(bili, "_view", side_effect=boom),
            patch.object(bili, "_keyword_search", side_effect=should_not_keyword),
        ):
            hits = await bili.search(_BV)
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
