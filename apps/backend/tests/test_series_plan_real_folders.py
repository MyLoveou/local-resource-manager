"""真实目录形态：第二季用 `II` 后缀、同目录混着 Music/IV/无集号文件。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.series_plan import (
    episode_number_from_stem,
    explain_series_plan,
    season_from_stem_suffix,
)

S1 = "[VCB-Studio] Kami nomi zo Shiru Sekai [{:02d}][Ma10p_1080p][x265_flac].mkv"
S2 = "[VCB-Studio] Kami nomi zo Shiru Sekai II [{:02d}][Ma10p_1080p][x265_flac].mkv"
IDOL = "[VCB-Studio] Kami nomi zo Shiru Sekai 4-nin to Idol [Ma10p_1080p][x265_flac].mkv"
GNCA = "GNCA-021002.mkv"
OVA_IV = "[VCB-Studio] Kami nomi zo Shiru Sekai [IV][Ma10p_480p][x265_2aac].mkv"
MUSIC = "[VCB-Studio] Kami nomi zo Shiru Sekai [Music{:02d}(All 4 You)][Ma10p_1080p][x265_flac].mkv"


class SeasonSuffixTests(unittest.TestCase):
    def test_roman_suffix_is_season(self) -> None:
        self.assertEqual(season_from_stem_suffix("[VCB-Studio] Sekai II [01][1080p]"), 2)
        self.assertEqual(season_from_stem_suffix("Show III [03]"), 3)

    def test_bracketed_roman_is_not_season(self) -> None:
        self.assertIsNone(season_from_stem_suffix("[VCB-Studio] Sekai [IV][Ma10p_480p]"))

    def test_ordinal_and_named(self) -> None:
        self.assertEqual(season_from_stem_suffix("Show 2nd Season [01]"), 2)
        self.assertEqual(season_from_stem_suffix("Show Season 3 [01]"), 3)

    def test_plain_name_has_no_season(self) -> None:
        self.assertIsNone(season_from_stem_suffix("[VCB-Studio] Sekai [01][1080p]"))


class RealFolderPlanTests(unittest.TestCase):
    def _plan(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "只有神知道的世界"
        root.mkdir()
        names = []
        for number in range(1, 11):
            names.append(S1.format(number))
        for number in range(1, 10):
            names.append(S2.format(number))
        names.append(IDOL)
        names.append(GNCA)
        names.append(OVA_IV)
        for number in range(1, 8):
            names.append(MUSIC.format(number))
        for name in names:
            (root / name).write_bytes(b"")
        return explain_series_plan(root, sorted(root.glob("*.mkv")))

    def test_plan_succeeds(self) -> None:
        plan = self._plan()
        self.assertTrue(plan.ok, plan.code)

    def test_second_season_is_separate(self) -> None:
        episodes = [item for item in self._plan().items if item.kind == "episode"]
        seasons = sorted({item.season for item in episodes})
        self.assertEqual(seasons, [1, 2])
        self.assertEqual(len([e for e in episodes if e.season == 1]), 10)
        self.assertEqual(len([e for e in episodes if e.season == 2]), 9)

    def test_music_and_unparsed_go_to_extras(self) -> None:
        extras = [item for item in self._plan().items if item.kind == "extra"]
        titles = " | ".join(item.title for item in extras)
        self.assertIn("Music", titles)
        self.assertIn("Idol", titles)
        self.assertIn("GNCA", titles)
        self.assertIn("IV", titles)

    def test_no_auto_numbering_when_others_parse(self) -> None:
        plan = self._plan()
        self.assertNotIn("自动编号", plan.message)

    def test_episode_numbers_still_parse(self) -> None:
        self.assertEqual(episode_number_from_stem(S1.format(3)), 3)
        self.assertEqual(episode_number_from_stem(S2.format(3)), 3)
