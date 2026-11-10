"""平铺目录：正片与 OVA 都在同一层，靠文件名前缀区分。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.series_plan import explain_series_plan

MAIN = "[VCB-Studio] Kami nomi zo Shiru Sekai [{:02d}][Ma10p_1080p][x265_flac].mkv"
MEGAMI = "[VCB-Studio] Kami nomi zo Shiru Sekai Megami Hen [{:02d}][Ma10p_1080p][x265_flac_aac].mkv"
TENRI = "[VCB-Studio] Kami nomi zo Shiru Sekai Tenri Hen [{:02d}][Ma10p_1080p][x265_flac].mkv"


class FlatMixedOvaTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "[VCB-Studio] Kami nomi zo Shiru Sekai"
        self.root.mkdir()
        for number in range(1, 13):
            (self.root / MAIN.format(number)).write_bytes(b"")
        for number in range(1, 13):
            (self.root / MEGAMI.format(number)).write_bytes(b"")
        for number in range(1, 15):
            (self.root / TENRI.format(number)).write_bytes(b"")
        self.videos = sorted(self.root.glob("*.mkv"))

    def test_plan_succeeds(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        self.assertTrue(plan.ok, f"{plan.code}: {plan.details[:2]}")

    def test_main_series_is_twelve_episodes(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        episodes = [item for item in plan.items if item.kind == "episode"]
        self.assertEqual(len(episodes), 12)
        self.assertEqual(sorted(item.episode for item in episodes), list(range(1, 13)))

    def test_ova_prefixes_become_extras(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        extras = [item for item in plan.items if item.kind == "extra"]
        self.assertEqual(len(extras), 26)
        titles = " | ".join(item.title for item in extras)
        self.assertIn("Megami Hen", titles)
        self.assertIn("Tenri Hen", titles)


class FlatSeasonSuffixTests(unittest.TestCase):
    """`Sekai II` 这类后缀仍然是同一部片子的第二季，不能被当特典。"""

    def test_roman_season_stays_episodes(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "show"
        root.mkdir()
        videos = []
        for number in range(1, 4):
            path = root / f"[Group] Show [{number:02d}][1080p].mkv"
            path.write_bytes(b"")
            videos.append(path)
            path2 = root / f"[Group] Show II [{number:02d}][1080p].mkv"
            path2.write_bytes(b"")
            videos.append(path2)
        plan = explain_series_plan(root, sorted(videos))
        self.assertTrue(plan.ok, plan.code)
        self.assertEqual(len([i for i in plan.items if i.kind == "episode"]), 6)
        self.assertEqual(len([i for i in plan.items if i.kind == "extra"]), 0)
