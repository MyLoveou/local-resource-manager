"""刮削任务：search 不改标题；select 才回填。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.covers.origin import COVER_ORIGIN_USER, merge_cover_origin
from app.library.infrastructure.repositories import ResourceRepository
from app.scrape.application.jobs import ScrapeError, create_or_reuse_job, run_search, select_candidate
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.scrape.infrastructure.repo import ScrapeRepository
from app.shared.db.migrations import migrate
from app.library.domain.models import (
    Resource,
    ResourceStatus,
    ResourceType,
    WorkCatalog,
)


class FakeProvider(MetadataProvider):
    def __init__(self, hits: list[SearchHit] | None = None, payload: ScrapeDetail | None = None) -> None:
        self.hits = hits or [
            SearchHit(title="外部片名", key="fake:1", source="fake", thumbnail_url=None, relevance=1.0)
        ]
        self.payload = payload or ScrapeDetail(
            title="确认后的标题",
            synopsis="简介",
            tags=["科幻"],
            poster_url=None,
            catalog=WorkCatalog(original_title="EN Title", source="fake", source_id="1"),
            source_ref="fake:1",
        )
        self.search_calls = 0

    async def search(self, query: str) -> list[SearchHit]:
        self.search_calls += 1
        return list(self.hits)

    async def detail(self, key: str) -> ScrapeDetail:
        return self.payload


class ScrapeJobsTests(unittest.IsolatedAsyncioTestCase):
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
        self.fake = FakeProvider()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self._tmp.cleanup()

    async def _video(self, session, title: str = "clip.mp4") -> Resource:
        repo = ResourceRepository(session)
        return await repo.create(
            Resource(type=ResourceType.VIDEO, title=title, status=ResourceStatus.ACTIVE)
        )

    async def test_search_does_not_change_title(self) -> None:
        async with self.factory() as session:
            created = await self._video(session)
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, job.id)
            fresh = await ResourceRepository(session).get(created.id)
            self.assertEqual(fresh.title, "clip.mp4")
            self.assertTrue(fresh.scrape_pending)
            cands = await ScrapeRepository(session).list_candidates(job.id)
            self.assertEqual(len(cands), 1)

    async def test_select_overwrites_title_and_unions_tags(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            created = await self._video(session)
            created.description = "我写的评价"
            await repo.update(created.id, created)
            await repo.add_tags_union(created.id, ["已有"])
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, job.id)
                cands = await ScrapeRepository(session).list_candidates(job.id)
                await select_candidate(session, job.id, cands[0].id)
            fresh = await repo.get(created.id)
            self.assertEqual(fresh.title, "确认后的标题")
            self.assertEqual(fresh.description, "我写的评价")
            self.assertEqual(fresh.synopsis, "简介")
            self.assertEqual(fresh.catalog.original_title if fresh.catalog else None, "EN Title")
            self.assertFalse(fresh.scrape_pending)
            names = sorted(t.name for t in fresh.tags)
            self.assertEqual(names, ["已有", "科幻"])

    async def test_select_skips_title_when_unchecked(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            created = await self._video(session)
            created.author = "已有作者"
            await repo.update(created.id, created)
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, job.id)
                cands = await ScrapeRepository(session).list_candidates(job.id)
                await select_candidate(
                    session,
                    job.id,
                    cands[0].id,
                    apply_title=False,
                    apply_author=False,
                    apply_cover=False,
                )
            fresh = await repo.get(created.id)
            self.assertEqual(fresh.title, "clip.mp4")
            self.assertEqual(fresh.author, "已有作者")
            self.assertEqual(fresh.synopsis, "简介")

    async def test_user_cover_not_replaced(self) -> None:
        self.fake.payload = ScrapeDetail(
            title="新标题",
            synopsis=None,
            tags=[],
            poster_url="https://lain.bgm.tv/p.png",
            cover_urls=["https://lain.bgm.tv/p.png"],
            source_ref="fake:1",
        )
        async with self.factory() as session:
            repo = ResourceRepository(session)
            created = await self._video(session)
            created.cover_path = "/keep"
            created.extra = merge_cover_origin(created.extra, COVER_ORIGIN_USER)
            await repo.update(created.id, created)
            job = await create_or_reuse_job(session, created.id)
            with (
                patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]),
                patch("app.scrape.application.jobs.provider_for_key", return_value=self.fake),
            ):
                await run_search(session, job.id)
                cands = await ScrapeRepository(session).list_candidates(job.id)
                await select_candidate(session, job.id, cands[0].id)
            fresh = await repo.get(created.id)
            self.assertEqual(fresh.cover_path, "/keep")
            self.assertEqual((fresh.extra or {}).get("coverOrigin"), COVER_ORIGIN_USER)


    async def test_non_scrapeable_rejected(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            img = await repo.create(
                Resource(type=ResourceType.AV, title="clip", status=ResourceStatus.ACTIVE)
            )
            with self.assertRaises(ScrapeError) as ctx:
                await create_or_reuse_job(session, img.id)
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_force_creates_new_job(self) -> None:
        async with self.factory() as session:
            created = await self._video(session)
            first = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, first.id)
            reused = await create_or_reuse_job(session, created.id, force=False)
            self.assertEqual(reused.id, first.id)
            forced = await create_or_reuse_job(session, created.id, force=True)
            self.assertNotEqual(forced.id, first.id)

    async def test_empty_hits_not_pending(self) -> None:
        self.fake.hits = []
        async with self.factory() as session:
            created = await self._video(session)
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, job.id)
            fresh = await ResourceRepository(session).get(created.id)
            self.assertFalse(fresh.scrape_pending)

    async def test_secondary_channel_used_when_primary_fails(self) -> None:
        class Boom(MetadataProvider):
            async def search(self, query: str) -> list[SearchHit]:
                raise RuntimeError("主源失败")

            async def detail(self, key: str) -> ScrapeDetail:
                raise RuntimeError("不该走到")

        extra = FakeProvider(
            hits=[SearchHit(title="蜜柑名", key="mikan:9", source="mikan", relevance=0.4)]
        )
        async with self.factory() as session:
            created = await self._video(session)
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[Boom(), extra]):
                await run_search(session, job.id)
            cands = await ScrapeRepository(session).list_candidates(job.id)
            self.assertEqual(len(cands), 1)
            self.assertEqual(cands[0].source, "mikan")
            fresh = await ResourceRepository(session).get(created.id)
            self.assertEqual(fresh.title, "clip.mp4")


    async def test_tmdb_key_missing_still_keeps_bilibili_hits(self) -> None:
        class NoKey(MetadataProvider):
            async def search(self, query: str) -> list[SearchHit]:
                raise RuntimeError("未配置 TMDB API Key")

            async def detail(self, key: str) -> ScrapeDetail:
                raise RuntimeError("不该走到")

        extra = FakeProvider(
            hits=[SearchHit(title="投稿", key="bilibili:BV1xx411c7mD", source="bilibili", relevance=1.0)]
        )
        async with self.factory() as session:
            created = await self._video(session)
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[NoKey(), extra]):
                await run_search(session, job.id)
            cands = await ScrapeRepository(session).list_candidates(job.id)
            self.assertEqual(cands[0].source, "bilibili")
            saved = await ScrapeRepository(session).get_job(job.id)
            self.assertEqual(saved.status.value, "done")
    def test_parse_search_hits_unique(self) -> None:
        from app.scrape.application.providers.mikan import parse_search_hits

        html = """
        <a href="/Home/Bangumi/12">无职转生 第三季</a>
        <a href="/Home/Bangumi/12">重复</a>
        <a href="/Home/Bangumi/13">第二季</a>
        """
        hits = parse_search_hits(html, "无职")
        self.assertEqual([h.key for h in hits], ["mikan:12", "mikan:13"])
        self.assertEqual(hits[0].title, "无职转生 第三季")

    def test_parse_bangumi_page_bgm_id(self) -> None:
        from app.scrape.application.providers.mikan import parse_bangumi_page

        html = """
        <meta property="og:title" content="无职转生" />
        <meta property="og:image" content="/images/Bangumi/x.jpg" />
        <a href="https://bgm.tv/subject/270778">Bangumi</a>
        """
        title, poster, bgm = parse_bangumi_page(html, "12", "https://mikanani.kas.pub")
        self.assertEqual(title, "无职转生")
        self.assertEqual(poster, "https://mikanani.kas.pub/images/Bangumi/x.jpg")
        self.assertEqual(bgm, "270778")

    def test_poster_hosts_are_exact(self) -> None:
        from app.scrape.application.images import allowed_poster

        self.assertTrue(allowed_poster("https://lain.bgm.tv/pic/cover/l/x.jpg"))
        self.assertTrue(allowed_poster("http://lain.bgm.tv/pic/cover/l/x.jpg"))
        self.assertTrue(allowed_poster("https://i0.hdslb.com/bfs/archive/x.jpg"))
        self.assertFalse(allowed_poster("https://evilmikanani.me/x.png"))
        self.assertFalse(allowed_poster("https://api.bgm.tv/v0/subjects/1"))
        self.assertFalse(allowed_poster("https://evilhdslb.com/x.jpg"))


if __name__ == "__main__":
    unittest.main()
