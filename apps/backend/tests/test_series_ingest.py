"""番剧/AV 作品级入库与季集树。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.api.imports import validate_import
from app.library.application.import_service import ImportService
from app.library.application.schemas import ImportCreate
from app.library.application.series_plan import plan_series_videos
from app.library.infrastructure.import_job_store import ImportJobState
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.db.migrations import migrate
from app.shared.fs.file_ops import FileOps
from app.shared.models import Resource, ResourceStatus, ResourceType


class SeriesPlanTests(unittest.TestCase):
    def test_season_dir_and_sxxexx(self) -> None:
        root = Path("Show")
        a = root / "Season 01" / "01.mkv"
        b = root / "Season 01" / "02.mkv"
        plan = plan_series_videos(root, [a, b])
        assert plan is not None
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0].season, 1)
        self.assertEqual(plan[0].episode, 1)
        self.assertTrue(plan[0].dest_rel.endswith("S01E01.mkv"))

    def test_flat_sxxexx(self) -> None:
        root = Path("Show")
        plan = plan_series_videos(
            root,
            [root / "Title - S01E01.mkv", root / "Title - S01E02.mkv"],
        )
        assert plan is not None
        self.assertEqual([p.episode for p in plan], [1, 2])

    def test_unparseable_fails(self) -> None:
        root = Path("Show")
        self.assertIsNone(plan_series_videos(root, [root / "random.mkv"]))

    def test_snow_raws_wa_and_tokuten(self) -> None:
        """BD 常见：第01話 + 映像特典/CM01(BD…)。"""
        root = Path("Show")
        plan = plan_series_videos(
            root,
            [
                root / "[Snow-Raws] Title 第01話(BD 1920x1080).mkv",
                root / "[Snow-Raws] Title 第02話(BD 1920x1080).mkv",
                root / "映像特典" / "[Snow-Raws] Title CM01(BD 1920x1080).mkv",
                root / "映像特典" / "[Snow-Raws] Title MENU01(BD 1920x1080).mkv",
                root / "映像特典" / "[Snow-Raws] Title SP01(BD 1920x1080).mkv",
            ],
        )
        assert plan is not None
        episodes = [item for item in plan if item.kind == "episode"]
        extras = [item for item in plan if item.kind == "extra"]
        self.assertEqual([item.episode for item in episodes], [1, 2])
        self.assertEqual(len(extras), 3)

    def test_dbd_bracket_episode_and_extra_dirs(self) -> None:
        """DBD-Raws：[01] 为集；menu/PV/NCOP&NCED/特典映像 为特典。"""
        root = Path("Show")
        plan = plan_series_videos(
            root,
            [
                root / "[DBD-Raws][Isekai Ojisan][01][1080P][BDRip].mkv",
                root / "[DBD-Raws][Isekai Ojisan][02][1080P][BDRip].mkv",
                root / "menu" / "[DBD-Raws][Isekai Ojisan][menu][01][1080P].mkv",
                root / "PV" / "[DBD-Raws][Isekai Ojisan][PV][01][1080P].mkv",
                root / "NCOP&NCED" / "[DBD-Raws][Isekai Ojisan][NCED1][1080P].mkv",
                root / "特典映像" / "[DBD-Raws][Isekai Ojisan][Tokuten][01][1080P].mkv",
            ],
        )
        assert plan is not None
        episodes = [item for item in plan if item.kind == "episode"]
        extras = [item for item in plan if item.kind == "extra"]
        self.assertEqual([item.episode for item in episodes], [1, 2])
        self.assertEqual(len(extras), 4)


class SeriesIngestTests(unittest.IsolatedAsyncioTestCase):
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

    def _mkv(self, relative: str, payload: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    async def test_t1_empty_anime_av_lists(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            self.assertEqual(await repo.list(ResourceType.ANIME, None, 10, 0, "desc"), [])
            self.assertEqual(await repo.list(ResourceType.AV, None, 10, 0, "desc"), [])

    async def test_t2_video_row_survives_migration(self) -> None:
        async with self.factory() as session:
            repo = ResourceRepository(session)
            row = await repo.create(
                Resource(type=ResourceType.VIDEO, title="clip", status=ResourceStatus.ACTIVE)
            )
            got = await repo.get(row.id)  # type: ignore[arg-type]
            assert got is not None
            self.assertEqual(got.type, ResourceType.VIDEO)

    async def test_t3_detail_has_episode_tree(self) -> None:
        show = self.root / "MyShow"
        self._mkv("MyShow/Season 01/01.mkv", b"ep1-bytes")
        self._mkv("MyShow/Season 01/02.mkv", b"ep2-bytes")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="s1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.ANIME, "directory", [str(show)]
            )
            self.assertEqual(job.imported, 1)
            items = await repo.list(ResourceType.ANIME, None, 10, 0, "desc")
            self.assertEqual(len(items), 1)
            assert items[0].id is not None
            detail = await repo.get(items[0].id)
            assert detail is not None
            episodes = [ep for season in detail.seasons for ep in season.episodes]
            self.assertEqual(len(episodes), 2)

    async def test_t4_one_folder_one_work(self) -> None:
        show = self.root / "FolderWork"
        self._mkv("FolderWork/S01E01.mkv", b"a-unique")
        self._mkv("FolderWork/S01E02.mkv", b"b-unique")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="s2")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.ANIME, "directory", [str(show)]
            )
            self.assertEqual(job.imported, 1)
            self.assertEqual(len(await repo.list(ResourceType.ANIME, None, 10, 0, "desc")), 1)
            self.assertEqual(await repo.list(ResourceType.VIDEO, None, 10, 0, "desc"), [])

    async def test_r1_single_file_video_still_imports(self) -> None:
        video = self.root / "clip.mp4"
        video.write_bytes(b"not-a-real-mp4")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="v1")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.VIDEO, "file", [str(video)]
            )
            self.assertEqual(job.imported, 1)
            self.assertEqual(len(await repo.list(ResourceType.VIDEO, None, 10, 0, "desc")), 1)

    def test_series_file_import_rejected(self) -> None:
        err = validate_import(
            ImportCreate.model_validate(
                {"type": "anime", "sourceKind": "file", "paths": [str(self.root / "a.mkv")]}
            )
        )
        self.assertEqual(err, "series import requires a directory")

    async def test_unparseable_dir_not_imported(self) -> None:
        folder = self.root / "Messy"
        self._mkv("Messy/random.mkv", b"x")
        async with self.factory() as session:
            repo = ResourceRepository(session)
            job = ImportJobState(id="bad")
            await ImportService(repo, store_root=self.store, file_ops=self.ops).run(
                job, ResourceType.ANIME, "directory", [str(folder)]
            )
            self.assertEqual(job.imported, 0)
            self.assertGreaterEqual(job.skipped_error, 1)


if __name__ == "__main__":
    unittest.main()
