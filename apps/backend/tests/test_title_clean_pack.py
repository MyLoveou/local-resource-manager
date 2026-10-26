"""作品标题清洗：打包说明（集数范围 / 全集 / 特典 / 语言包装）不进标题。

线上问题：`[DBD-Raws][异世界舅舅][01-13TV全集+特典映像][1080P][BDRip][HEVC-10bit][简繁日双语外挂][FLAC][MKV]`
清洗后仍是 `异世界舅舅01-13TV全集+特典映像简繁日双语外挂`——因为噪音表里既没有
集数范围，也没有中文的打包/语言标记。
"""

from __future__ import annotations

import unittest

from app.library.application.smart_import.title_clean import (
    clean_release_name,
    describe_removed,
)

DBD = (
    "[DBD-Raws][异世界舅舅][01-13TV全集+特典映像][1080P][BDRip]"
    "[HEVC-10bit][简繁日双语外挂][FLAC][MKV]"
)


class WorkTitleTests(unittest.TestCase):
    def test_pack_segment_is_dropped_for_work_title(self) -> None:
        result = clean_release_name(DBD, keep_episode=False)
        self.assertEqual(result.title, "异世界舅舅")

    def test_episode_range_alone_is_dropped(self) -> None:
        result = clean_release_name("[Group] 某番 [01-12][1080p]", keep_episode=False)
        self.assertEqual(result.title, "某番")

    def test_full_collection_marker_is_dropped(self) -> None:
        result = clean_release_name("[Group] 某番 [全12话][1080p]", keep_episode=False)
        self.assertEqual(result.title, "某番")

    def test_language_packaging_is_dropped(self) -> None:
        result = clean_release_name("[Group] 某番 [简繁日双语外挂][1080p]", keep_episode=False)
        self.assertEqual(result.title, "某番")

    def test_extra_marker_is_dropped_for_work_title(self) -> None:
        result = clean_release_name("[Group] 某番 [特典映像][1080p]", keep_episode=False)
        self.assertEqual(result.title, "某番")

    def test_plain_title_is_unchanged(self) -> None:
        result = clean_release_name("异世界舅舅", keep_episode=False)
        self.assertEqual(result.title, "异世界舅舅")
        self.assertEqual(result.confidence, 0.0)

    def test_reason_lists_what_was_removed(self) -> None:
        result = clean_release_name(DBD, keep_episode=False)
        reason = describe_removed(result.removed)
        self.assertIn("01-13TV全集+特典映像", reason)


class SingleFileTitleTests(unittest.TestCase):
    """单文件视频靠集号与特典词区分，不能为了干净而撞名。"""

    def test_episode_number_is_kept(self) -> None:
        result = clean_release_name(
            "[VCB-Studio] Sousou no Frieren [01][Ma10p_1080p][x265_flac]"
        )
        self.assertEqual(result.title, "Sousou no Frieren 01")

    def test_extra_word_survives_for_single_file(self) -> None:
        result = clean_release_name(
            "[DBD-Raws][异世界舅舅][Tokuten][02][1080P][BDRip][HEVC-10bit][FLAC][MKV]"
        )
        self.assertIn("Tokuten", result.title)
        self.assertIn("02", result.title)

    def test_pack_segment_still_dropped_for_single_file(self) -> None:
        result = clean_release_name(DBD)
        self.assertNotIn("01-13", result.title)
