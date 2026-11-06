"""根目录有正片、子文件夹放 OVA（Megami Hen / Tenri Hen）时的拆分。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.series_plan import explain_series_plan

S1 = "[VCB-Studio] Kami nomi zo Shiru Sekai [{:02d}][Ma10p_1080p][x265_flac].mkv"
MEGAMI = "[VCB-Studio] Kami nomi zo Shiru Sekai Megami Hen [{:02d}][Ma10p_1080p][x265_flac].mkv"
TENRI = "[VCB-Studio] Kami nomi zo Shiru Sekai Tenri Hen [{:02d}][Ma10p_1080p][x265_flac].mkv"


def _build(root: Path) -> list[Path]:
    for number in range(1, 13):
        (root / S1.format(number)).write_bytes(b"")
    for folder, pattern, count in (("Megami Hen", MEGAMI, 12), ("Tenri Hen", TENRI, 14)):
        sub = root / folder
        sub.mkdir()
        for number in range(1, count + 1):
            (sub / pattern.format(number)).write_bytes(b"")
    return sorted(root.rglob("*.mkv"))


class SubfolderOvaTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "Kami nomi zo Shiru Sekai"
        self.root.mkdir()
        self.videos = _build(self.root)

    def test_plan_succeeds(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        self.assertTrue(plan.ok, f"{plan.code}: {plan.details[:2]}")

    def test_only_root_files_are_episodes(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        episodes = [item for item in plan.items if item.kind == "episode"]
        self.assertEqual(len(episodes), 12)
        self.assertEqual(sorted(item.episode for item in episodes), list(range(1, 13)))

    def test_ova_folders_become_extras(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        extras = [item for item in plan.items if item.kind == "extra"]
        self.assertEqual(len(extras), 26)
        titles = " | ".join(item.title for item in extras)
        self.assertIn("Megami Hen", titles)
        self.assertIn("Tenri Hen", titles)

    def test_extras_titles_are_cleaned(self) -> None:
        plan = explain_series_plan(self.root, self.videos)
        extra = next(item for item in plan.items if item.kind == "extra")
        self.assertNotIn("[VCB-Studio]", extra.title)
        self.assertNotIn("Ma10p", extra.title)


class SeasonDirTests(unittest.TestCase):
    """季目录仍然必须当正片，不能被当成特典。"""

    def test_season_directory_stays_episodes(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "Show"
        (root / "Season 01").mkdir(parents=True)
        (root / "Season 02").mkdir(parents=True)
        videos = []
        for season in ("Season 01", "Season 02"):
            for number in range(1, 4):
                path = root / season / f"S{season[-1]}E{number:02d}.mkv"
                path.write_bytes(b"")
                videos.append(path)
        plan = explain_series_plan(root, sorted(videos))
        self.assertTrue(plan.ok, plan.code)
        self.assertEqual(len([item for item in plan.items if item.kind == "episode"]), 6)
        self.assertEqual(len([item for item in plan.items if item.kind == "extra"]), 0)
