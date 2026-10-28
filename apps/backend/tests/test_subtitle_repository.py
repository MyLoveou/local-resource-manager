"""抽帧封装与 subtitle_tracks 仓储的测试（不依赖真实 ffmpeg）。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.library.application.episode_covers import extract_cover, ffmpeg_available
from app.library.infrastructure.repositories_subtitles import SubtitleRepository
from app.shared.db.migrations import migrate


class CoverTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.video = self.root / "v.mkv"
        self.video.write_bytes(b"video")
        self.output = self.root / "covers" / "ep.jpg"

    def test_no_ffmpeg_returns_false(self) -> None:
        with patch("app.library.application.episode_covers.shutil.which", return_value=None):
            self.assertFalse(ffmpeg_available())
            self.assertFalse(extract_cover(self.video, self.output))
        self.assertFalse(self.output.exists())

    def test_success_writes_file(self) -> None:
        def fake_run(command, **_kwargs):
            Path(command[-1]).write_bytes(b"jpg")
            return type("R", (), {"returncode": 0})()

        with patch("app.library.application.episode_covers.shutil.which", return_value="ffmpeg"), patch(
            "app.library.application.episode_covers.subprocess.run", side_effect=fake_run
        ):
            self.assertTrue(extract_cover(self.video, self.output))
        self.assertTrue(self.output.exists())

    def test_nonzero_exit_returns_false(self) -> None:
        def fake_run(command, **_kwargs):
            return type("R", (), {"returncode": 1})()

        with patch("app.library.application.episode_covers.shutil.which", return_value="ffmpeg"), patch(
            "app.library.application.episode_covers.subprocess.run", side_effect=fake_run
        ):
            self.assertFalse(extract_cover(self.video, self.output))

    def test_missing_video_returns_false(self) -> None:
        with patch("app.library.application.episode_covers.shutil.which", return_value="ffmpeg"):
            self.assertFalse(extract_cover(self.root / "nope.mkv", self.output))


class SubtitleRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "t.db"
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.close()
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")

        @event.listens_for(self.engine.sync_engine, "connect")
        def _on_connect(dbapi_conn, _record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def _seed(self, session) -> tuple[int, int, int, int]:
        await session.execute(
            text("INSERT INTO resources (type, title) VALUES ('anime', 't')")
        )
        rid = int(await session.scalar(text("SELECT MAX(id) FROM resources")))
        await session.execute(
            text(
                "INSERT INTO files (resource_id, path, sha256, size, format, role) "
                "VALUES (:r, 'p', 'h', 0, 'mkv', 'primary')"
            ),
            {"r": rid},
        )
        primary = int(await session.scalar(text("SELECT MAX(id) FROM files")))
        await session.execute(
            text(
                "INSERT INTO files (resource_id, path, sha256, size, format, role) "
                "VALUES (:r, 's.srt', 'h2', 0, 'srt', 'subtitle')"
            ),
            {"r": rid},
        )
        subtitle = int(await session.scalar(text("SELECT MAX(id) FROM files")))
        await session.execute(
            text("INSERT INTO seasons (resource_id, season_number) VALUES (:r, 1)"),
            {"r": rid},
        )
        season = int(await session.scalar(text("SELECT MAX(id) FROM seasons")))
        await session.execute(
            text(
                "INSERT INTO episodes (season_id, file_id, episode_number) VALUES (:s, :f, 1)"
            ),
            {"s": season, "f": primary},
        )
        episode = int(await session.scalar(text("SELECT MAX(id) FROM episodes")))
        return rid, subtitle, episode, primary

    async def test_attach_is_idempotent_and_listed(self) -> None:
        async with self.factory() as session:
            rid, subtitle, episode, _ = await self._seed(session)
            repo = SubtitleRepository(session)
            await repo.attach(rid, subtitle, episode_id=episode, language="zh-Hans")
            await repo.attach(rid, subtitle, episode_id=episode, language="zh-Hans")
            await session.commit()
            rows = await repo.list_for_resource(rid)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["language"], "zh-Hans")

    async def test_resource_level_track(self) -> None:
        async with self.factory() as session:
            rid, subtitle, _, _ = await self._seed(session)
            repo = SubtitleRepository(session)
            await repo.attach(rid, subtitle)
            await session.commit()
            rows = await repo.list_for_resource(rid)
            self.assertEqual(len(rows), 1)
            self.assertIsNone(rows[0]["episode_id"])

    async def test_detach_removes_only_link(self) -> None:
        async with self.factory() as session:
            rid, subtitle, episode, _ = await self._seed(session)
            repo = SubtitleRepository(session)
            await repo.attach(rid, subtitle, episode_id=episode)
            await session.commit()
            track_id = (await repo.list_for_episode(episode))[0]["id"]
            self.assertTrue(await repo.detach(track_id))
            await session.commit()
            self.assertEqual(await repo.list_for_episode(episode), [])
            remaining = await session.scalar(
                text("SELECT COUNT(*) FROM files WHERE id = :id"), {"id": subtitle}
            )
            self.assertEqual(remaining, 1)
