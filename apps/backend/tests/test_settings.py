"""设置：掩码、env 优先、备份。"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.settings.application.errors import SettingsError
from app.settings.application.schemas import ScrapeSettingsPatch, SystemSettingPatch
from app.settings.application.secrets import invalidate_secret_cache, tmdb_api_key
from app.settings.application.service import backup_database, backup_library, get_view, patch_scrape, pathc_system_settings
from app.settings.application.restore import prepare_restore
from app.settings.application import restore as restore_module
from app.shared.db.migrations import migrate
from app.shared import config
from app.shared.runtime_paths import set_library_root


class SettingsTests(unittest.IsolatedAsyncioTestCase):
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
        invalidate_secret_cache()
        self._db_patch = patch.object(config.settings, "db_path", self.db_path)
        self._db_patch.start()
        self._env = patch.dict(
            os.environ,
            {"TMDB_API_KEY": "", "BANGUMI_ACCESS_TOKEN": "", "MIKAN_BASE_URL": ""},
        )
        self._env.start()

    async def asyncTearDown(self) -> None:
        self._env.stop()
        self._db_patch.stop()
        set_library_root(None)
        invalidate_secret_cache()
        await self.engine.dispose()
        self._tmp.cleanup()

    async def test_patch_masked_and_readable(self) -> None:
        async with self.factory() as session:
            view = await patch_scrape(
                session,
                ScrapeSettingsPatch(tmdb_api_key="secretkey9999"),
                self.db_path,
                "0.0.0",
            )
            dumped = view.model_dump_json()
            self.assertNotIn("secretkey9999", dumped)
            self.assertTrue(view.scrape.tmdb.configured)
            self.assertEqual(view.scrape.tmdb.hint, "••••9999")
        self.assertEqual(tmdb_api_key(), "secretkey9999")

    async def test_env_blocks_patch(self) -> None:
        os.environ["TMDB_API_KEY"] = "fromenv1234"
        invalidate_secret_cache()
        async with self.factory() as session:
            with self.assertRaises(SettingsError) as ctx:
                await patch_scrape(
                    session,
                    ScrapeSettingsPatch(tmdb_api_key="other"),
                    self.db_path,
                    "0.0.0",
                )
            self.assertEqual(ctx.exception.status_code, 400)
            view = await get_view(session, self.db_path, "0.0.0")
            self.assertTrue(view.scrape.tmdb.env_locked)
        self.assertEqual(tmdb_api_key(), "fromenv1234")

    async def test_system_paths_roundtrip(self) -> None:
        library = self.root / "media"
        extra = self.root / "logs-custom"
        library.mkdir()
        extra.mkdir()
        async with self.factory() as session:
            view = await pathc_system_settings(
                session,
                SystemSettingPatch(library_path=str(library), log_dir=str(extra)),
                self.db_path,
                "0.0.0",
            )
            self.assertEqual(Path(view.system.library_path), library.resolve())
            self.assertEqual(Path(view.system.log_dir), extra.resolve())
            self.assertEqual(Path(view.system.db_path), self.db_path.resolve())
            again = await pathc_system_settings(
                session,
                SystemSettingPatch(backup_dir=str(self.root / "bak")),
                self.db_path,
                "0.0.0",
            )
            self.assertEqual(Path(again.system.library_path), library.resolve())
            self.assertTrue(again.system.backup_dir.endswith("bak"))

    def test_backup_readable(self) -> None:
        result = backup_database(self.db_path)
        dest = Path(result.path)
        self.assertTrue(dest.is_file())
        conn = sqlite3.connect(dest)
        try:
            count = conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
            self.assertGreaterEqual(count, 0)
        finally:
            conn.close()

    def test_full_backup_contains_database_and_library(self) -> None:
        thumb = self.root / "library" / "image" / "1" / "thumbs" / "grid.webp"
        thumb.parent.mkdir(parents=True)
        thumb.write_bytes(b"thumb")
        result = backup_library(self.db_path)
        dest = Path(result.path)
        self.assertTrue(dest.is_file())
        with zipfile.ZipFile(dest) as archive:
            names = set(archive.namelist())
        self.assertIn("library.db", names)
        self.assertIn("library/image/1/thumbs/grid.webp", names)

    def test_prepare_restore_rejects_unsafe_member(self) -> None:
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.write(self.db_path, "library.db")
            zipped.writestr("../outside.txt", "x")
        with self.assertRaises(SettingsError):
            prepare_restore(self.db_path, archive)

    def test_prepare_restore_rejects_missing_database(self) -> None:
        archive = self.root / "missing-db.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("library/image/1/primary.jpg", "x")
        with self.assertRaises(SettingsError):
            prepare_restore(self.db_path, archive)

    def test_prepare_restore_rejects_member_limit(self) -> None:
        archive = self.root / "many-members.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.write(self.db_path, "library.db")
            zipped.writestr("library/a.jpg", "x")
        with patch.object(restore_module, "_MAX_MEMBERS", 1):
            with self.assertRaises(SettingsError):
                prepare_restore(self.db_path, archive)

    def test_prepare_restore_rejects_uncompressed_limit(self) -> None:
        archive = self.root / "large-uncompressed.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.write(self.db_path, "library.db")
            zipped.writestr("library/a.jpg", "x" * 1024)
        with patch.object(restore_module, "_MAX_UNCOMPRESSED_BYTES", 512):
            with self.assertRaises(SettingsError):
                prepare_restore(self.db_path, archive)
