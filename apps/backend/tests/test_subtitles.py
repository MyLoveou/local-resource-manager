"""字幕发现/匹配与迁移 0033 的单元测试。"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.library.application.subtitles import (
    discover_subtitles,
    episode_number,
    infer_language,
    is_renderable,
    match_all,
    match_subtitle,
    similarity,
)
from app.shared.db.migrations import migrate

VIDEO = "[DBD-Raws][Isekai Ojisan][03][1080P][BDRip][HEVC-10bit][FLAC].mkv"


class DiscoverTests(unittest.TestCase):
    def _root(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_finds_subtitle_next_to_video(self) -> None:
        root = self._root()
        (root / "a.ass").write_text("", encoding="utf-8")
        (root / "a.mkv").write_text("", encoding="utf-8")
        self.assertEqual([p.name for p in discover_subtitles(root)], ["a.ass"])

    def test_finds_subtitle_in_subdirs(self) -> None:
        root = self._root()
        for sub in ("Subs", "字幕", "subtitles"):
            directory = root / sub
            directory.mkdir()
            (directory / f"{sub}.srt").write_text("", encoding="utf-8")
        names = sorted(p.name for p in discover_subtitles(root))
        self.assertEqual(names, ["Subs.srt", "subtitles.srt", "字幕.srt"])

    def test_ignores_non_subtitle(self) -> None:
        root = self._root()
        (root / "a.txt").write_text("", encoding="utf-8")
        (root / "a.mkv").write_text("", encoding="utf-8")
        self.assertEqual(discover_subtitles(root), [])

    def test_ignores_subtitle_far_from_root(self) -> None:
        root = self._root()
        deep = root / "other" / "nested"
        deep.mkdir(parents=True)
        (deep / "x.srt").write_text("", encoding="utf-8")
        self.assertEqual(discover_subtitles(root), [])


class EpisodeNumberTests(unittest.TestCase):
    def test_takes_last_standalone_number(self) -> None:
        self.assertEqual(episode_number(VIDEO), 3)

    def test_ignores_resolution(self) -> None:
        self.assertIsNone(episode_number("[Group] Title [1080P].mkv"))

    def test_chinese_marker(self) -> None:
        self.assertEqual(episode_number("[Group] 某番 第03话.mkv"), 3)


class MatchTests(unittest.TestCase):
    def test_episode_number_wins(self) -> None:
        video = Path("/x/[Group] Show [03][1080p].mkv")
        candidates = [Path("/x/[Group] Show [02].srt"), Path("/x/[Group] Show [03].srt")]
        self.assertEqual(match_subtitle(video, candidates), candidates[1])

    def test_similarity_fallback(self) -> None:
        video = Path("/x/Some Show Episode Name.mkv")
        candidate = Path("/x/Some Show Episode Name.srt")
        self.assertEqual(match_subtitle(video, [candidate]), candidate)

    def test_no_match_is_none(self) -> None:
        video = Path("/x/[Group] Alpha [03].mkv")
        self.assertIsNone(match_subtitle(video, [Path("/x/Complete Other Thing.srt")]))

    def test_all_matches_multi_language(self) -> None:
        videos = [Path("/x/[Group] Show [03].mkv")]
        candidates = [
            Path("/x/[Group] Show [03] CHS.srt"),
            Path("/x/[Group] Show [03] JPN.srt"),
            Path("/x/[Group] Show [04] CHS.srt"),
        ]
        result = match_all(videos, candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[videos[0]]), 2)

    def test_similarity_helper(self) -> None:
        self.assertGreater(similarity("Some Show 03.mkv", "Some Show 03.srt"), 0.9)


class LanguageTests(unittest.TestCase):
    def test_chinese_simplified(self) -> None:
        self.assertEqual(infer_language("Show [03] CHS.srt"), "zh-Hans")

    def test_japanese(self) -> None:
        self.assertEqual(infer_language("Show [03] JPN.srt"), "ja")

    def test_unknown(self) -> None:
        self.assertIsNone(infer_language("Show [03].srt"))

    def test_renderable(self) -> None:
        self.assertTrue(is_renderable(Path("a.srt")))
        self.assertTrue(is_renderable(Path("a.vtt")))
        self.assertFalse(is_renderable(Path("a.ass")))
        self.assertFalse(is_renderable(Path("a.ssa")))


class MigrationTests(unittest.TestCase):
    def test_0033_applies_and_cascades(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        conn = sqlite3.connect(Path(tmp.name) / "t.db")
        conn.row_factory = sqlite3.Row
        migrate(conn)
        conn.execute("PRAGMA foreign_keys=ON")

        columns = [row[1] for row in conn.execute("PRAGMA table_info(episodes)")]
        self.assertIn("cover_file_id", columns)

        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertIn("subtitle_tracks", tables)

        # 删除集后关联行应被级联清理
        conn.execute("INSERT INTO resources (type, title) VALUES ('anime','t')")
        rid = conn.execute("SELECT MAX(id) FROM resources").fetchone()[0]
        conn.execute(
            "INSERT INTO files (resource_id, path, sha256, size, format, role) "
            "VALUES (?, 'p', 'h', 0, 'mkv', 'primary')",
            (rid,),
        )
        fid = conn.execute("SELECT MAX(id) FROM files").fetchone()[0]
        conn.execute(
            "INSERT INTO seasons (resource_id, season_number) VALUES (?, 1)", (rid,)
        )
        sid = conn.execute("SELECT MAX(id) FROM seasons").fetchone()[0]
        conn.execute(
            "INSERT INTO episodes (season_id, file_id, episode_number) VALUES (?, ?, 1)",
            (sid, fid),
        )
        eid = conn.execute("SELECT MAX(id) FROM episodes").fetchone()[0]
        conn.execute(
            "INSERT INTO subtitle_tracks (resource_id, file_id, episode_id) VALUES (?, ?, ?)",
            (rid, fid, eid),
        )
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM subtitle_tracks").fetchone()[0], 1
        )
        conn.execute("DELETE FROM episodes WHERE id = ?", (eid,))
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM subtitle_tracks").fetchone()[0], 0
        )
        conn.close()
