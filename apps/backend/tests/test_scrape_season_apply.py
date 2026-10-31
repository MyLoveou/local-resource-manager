"""按季写入元数据：不动资源本身。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.domain.models import (
    Resource,
    ResourceStatus,
    ResourceType,
    WorkCatalog,
)
from app.library.infrastructure.repositories import ResourceRepository
from app.scrape.application.jobs import create_or_reuse_job, run_search, select_candidate
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.scrape.infrastructure.repo import ScrapeRepository
from app.shared.db.migrations import migrate


class FakeProvider(MetadataProvider):
    def __init__(self) -> None:
        self.hits = [SearchHit(title="第二季", key="fake:2", source="fake", relevance=1.0)]
        self.payload = ScrapeDetail(
            title="作品 第二季",
            synopsis="第二季简介",
            tags=[],
            poster_url=None,
            catalog=WorkCatalog(original_title="Season Two", source="fake", source_id="2"),
            source_ref="fake:2",
        )

    async def search(self, query: str) -> list[SearchHit]:
        return list(self.hits)

    async def detail(self, key: str) -> ScrapeDetail:
        return self.payload


class SeasonApplyTests(unittest.IsolatedAsyncioTestCase):
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

    async def _series(self, session) -> Resource:
        repo = ResourceRepository(session)
        created = await repo.create(
            Resource(type=ResourceType.ANIME, title="原作品名", status=ResourceStatus.ACTIVE)
        )
        await repo.add_season(created.id, 1, sort_index=1)
        await repo.add_season(created.id, 2, title="作品 II", sort_index=2)
        return created

    async def test_season_select_writes_catalog_only_to_season(self) -> None:
        async with self.factory() as session:
            created = await self._series(session)
            job = await create_or_reuse_job(session, created.id, query="作品 II")
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, job.id)
                candidates = await ScrapeRepository(session).list_candidates(job.id)
                await select_candidate(session, job.id, candidates[0].id, season=2)

            fresh = await ResourceRepository(session).get(created.id)
            # 资源标题没被覆盖
            self.assertEqual(fresh.title, "原作品名")

            conn2 = sqlite3.connect(self.db_path)
            first = conn2.execute(
                "SELECT title, catalog_json FROM seasons WHERE resource_id = ? AND season_number = 1",
                (created.id,),
            ).fetchone()
            title, catalog = conn2.execute(
                "SELECT title, catalog_json FROM seasons WHERE resource_id = ? AND season_number = 2",
                (created.id,),
            ).fetchone()
            conn2.close()
            self.assertIsNone(first[1])
            self.assertEqual(title, "作品 第二季")
            self.assertIn("Season Two", catalog or "")


class SeasonGuardTests(unittest.IsolatedAsyncioTestCase):
    """season 必须存在；否则 422，且资源与季都不能被改。"""

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

    async def test_missing_season_is_rejected(self) -> None:
        from app.scrape.application.jobs import ScrapeError

        async with self.factory() as session:
            repo = ResourceRepository(session)
            created = await repo.create(
                Resource(type=ResourceType.ANIME, title="原标题", status=ResourceStatus.ACTIVE)
            )
            await repo.add_season(created.id, 1, sort_index=1)
            job = await create_or_reuse_job(session, created.id)
            with patch("app.scrape.application.jobs.providers_for", return_value=[self.fake]), patch(
                "app.scrape.application.jobs.provider_for_key", return_value=self.fake
            ):
                await run_search(session, job.id)
                candidates = await ScrapeRepository(session).list_candidates(job.id)
                with self.assertRaises(ScrapeError):
                    await select_candidate(session, job.id, candidates[0].id, season=9)

            fresh = await ResourceRepository(session).get(created.id)
            self.assertEqual(fresh.title, "原标题")
            conn = sqlite3.connect(self.db_path)
            catalog = conn.execute(
                "SELECT catalog_json FROM seasons WHERE resource_id=? AND season_number=1",
                (created.id,),
            ).fetchone()[0]
            conn.close()
            self.assertIsNone(catalog)


class StrictModelTests(unittest.TestCase):
    """写入模型拒绝未知字段，避免旧后端静默忽略 season。"""

    def test_scrape_select_rejects_unknown_field(self) -> None:
        from pydantic import ValidationError

        from app.scrape.application.schemas import ScrapeSelect

        with self.assertRaises(ValidationError):
            ScrapeSelect(candidate_id=1, 不存在的字段=2)

    def test_season_is_accepted(self) -> None:
        from app.scrape.application.schemas import ScrapeSelect

        model = ScrapeSelect(candidateId=1, season=2)
        self.assertEqual(model.season, 2)