"""导入预览：目录扫描与计划摘要。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.import_preview import collect_videos, summarize
from app.library.application.series_plan import PlannedItem


class CollectTests(unittest.TestCase):
    def test_only_video_files(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "a.mkv").write_bytes(b"")
        (root / "b.mp4").write_bytes(b"")
        (root / "c.txt").write_bytes(b"")
        (root / ".hidden.mkv").write_bytes(b"")
        (root / "sub").mkdir()
        (root / "sub" / "d.mkv").write_bytes(b"")

        names = sorted(path.name for path in collect_videos(root))
        self.assertEqual(names, ["a.mkv", "b.mp4", "d.mkv"])


class SummarizeTests(unittest.TestCase):
    def _item(self, name: str, kind: str, season: int = 1, episode: int | None = 1, title=None):
        return PlannedItem(
            Path(name), kind, season, episode, f"seasons/{season:02d}/x{Path(name).suffix}", title
        )

    def test_groups_by_season(self) -> None:
        items = [
            self._item("s02e01.mkv", "episode", 2, 1),
            self._item("s01e02.mkv", "episode", 1, 2),
            self._item("s01e01.mkv", "episode", 1, 1, "开场"),
        ]
        summary = summarize(items)
        self.assertEqual(list(summary.seasons), [1, 2])
        self.assertEqual([ep.episode for ep in summary.seasons[1]], [1, 2])
        self.assertEqual(summary.seasons[1][0].title, "开场")

    def test_extras_are_separate(self) -> None:
        items = [
            self._item("a.mkv", "episode", 1, 1),
            self._item("ova.mkv", "extra", 0, None, "OVA 一"),
        ]
        summary = summarize(items)
        self.assertEqual(len(summary.extras), 1)
        self.assertEqual(summary.extras[0].title, "OVA 一")
        self.assertEqual(summary.total_files, 2)

    def test_empty_plan(self) -> None:
        summary = summarize([])
        self.assertEqual(summary.seasons, {})
        self.assertEqual(summary.extras, [])
        self.assertEqual(summary.total_files, 0)
