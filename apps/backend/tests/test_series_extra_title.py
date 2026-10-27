"""系列导入：特典标题要清洗，但保留 PV / 特典标记与番号。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.series_plan import explain_series_plan

ROOT = "[DBD-Raws][Isekai Ojisan][01-13TV全集+特典映像][1080P][BDRip][HEVC-10bit][FLAC]"
PV = "[DBD-Raws][Isekai Ojisan][PV][08][1080P][BDRip][HEVC-10bit][FLAC].mkv"
TOKUTEN = "[DBD-Raws][Isekai Ojisan][Tokuten][01][1080P][BDRip][HEVC-10bit][FLAC].mkv"
EPISODE = "[DBD-Raws][Isekai Ojisan][01][1080P][BDRip][HEVC-10bit][FLAC].mkv"


class ExtraTitleTests(unittest.TestCase):
    def _plan(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / ROOT
        root.mkdir()
        for name in (PV, TOKUTEN, EPISODE):
            (root / name).write_bytes(b"")
        videos = sorted(root.glob("*.mkv"))
        return explain_series_plan(root, videos)

    def test_extras_are_cleaned_but_keep_marker_and_number(self) -> None:
        plan = self._plan()
        titles = sorted(item.title for item in plan.items if item.kind == "extra")
        self.assertEqual(titles, ["Isekai Ojisan PV 08", "Isekai Ojisan 特典 01"])

    def test_episode_still_recognised(self) -> None:
        plan = self._plan()
        episodes = [item for item in plan.items if item.kind == "episode"]
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].episode, 1)
