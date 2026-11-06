"""发布组命名清洗（S1 · smart-import）。

两种语义：
- `keep_episode=True`（单文件视频 / 图片）：每个文件是独立资源，集号必须保留
- `keep_episode=False`（系列作品标题）：集号属于季/集树，不进作品名
"""
from __future__ import annotations

import unittest

from app.library.application.smart_import.title_clean import (
    clean_release_name,
    describe_removed,
)


class VideoTitleTests(unittest.TestCase):
    """单文件视频：清洗噪音，但保留集号。"""

    def test_vcb_brackets_stripped_episode_kept(self) -> None:
        result = clean_release_name(
            "[VCB-Studio] Sousou no Frieren [01][Ma10p_1080p][x265_flac]"
        )
        self.assertEqual(result.title, "Sousou no Frieren 01")
        self.assertEqual(len(result.removed), 3)
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_trailing_dash_episode_normalised(self) -> None:
        result = clean_release_name(
            "[Lilith-Raws] 葬送的芙莉莲 - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
        )
        self.assertEqual(result.title, "葬送的芙莉莲 01")
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_chinese_subgroup_marker(self) -> None:
        result = clean_release_name("[桜都字幕组] 葬送的芙莉莲 第01话 [1080p]")
        self.assertEqual(result.title, "葬送的芙莉莲 01")

    def test_episode_number_is_normalised(self) -> None:
        result = clean_release_name("[Group] Title - 7 [1080p]")
        self.assertEqual(result.title, "Title 07")

    def test_only_episode_number_yields_no_suggestion(self) -> None:
        """只有集号可动时不该出建议——否则多集会被改成同名。"""
        result = clean_release_name("夏日海边 01")
        self.assertEqual(result.title, "夏日海边 01")
        self.assertEqual(result.removed, ())
        self.assertEqual(result.confidence, 0.0)

    def test_clean_title_yields_no_suggestion(self) -> None:
        result = clean_release_name("夏日海边")
        self.assertEqual(result.title, "夏日海边")
        self.assertEqual(result.removed, ())
        self.assertEqual(result.confidence, 0.0)


class SeriesTitleTests(unittest.TestCase):
    """系列作品标题：季/集标记一律不进标题。"""

    def test_season_marker_removed(self) -> None:
        result = clean_release_name("葬送的芙莉莲 S01", keep_episode=False)
        self.assertEqual(result.title, "葬送的芙莉莲")
        self.assertIn("S01", " ".join(result.removed))

    def test_season_episode_removed(self) -> None:
        result = clean_release_name(
            "[VCB-Studio] Frieren S01E02 [1080p]", keep_episode=False
        )
        self.assertEqual(result.title, "Frieren")

    def test_chinese_season_and_episode_removed(self) -> None:
        result = clean_release_name("葬送的芙莉莲 第2季 第05话 [1080p]", keep_episode=False)
        self.assertEqual(result.title, "葬送的芙莉莲")

    def test_release_brackets_removed(self) -> None:
        result = clean_release_name(
            "[VCB-Studio] Sousou no Frieren [01][Ma10p_1080p]", keep_episode=False
        )
        self.assertEqual(result.title, "Sousou no Frieren")

    def test_plain_chinese_with_episode(self) -> None:
        result = clean_release_name("夏日海边 01", keep_episode=False)
        self.assertEqual(result.title, "夏日海边")
        self.assertLess(result.confidence, 0.85)
        self.assertGreater(result.confidence, 0.0)


class GenericTests(unittest.TestCase):
    def test_empty_result_falls_back_to_source(self) -> None:
        result = clean_release_name("[1080p][x265][AAC]")
        self.assertEqual(result.title, "[1080p][x265][AAC]")
        self.assertLess(result.confidence, 0.5)

    def test_blank_input(self) -> None:
        result = clean_release_name("   ")
        self.assertEqual(result.title, "")
        self.assertEqual(result.confidence, 0.0)

    def test_description_is_human_readable(self) -> None:
        result = clean_release_name("[VCB-Studio] Sousou no Frieren [01][1080p]")
        text = describe_removed(result.removed)
        self.assertIn("去掉了", text)
        self.assertIn("VCB-Studio", text)

    def test_does_not_touch_plain_prefix(self) -> None:
        result = clean_release_name("Frieren 葬送的芙莉莲 S01E02 1080p")
        self.assertTrue(result.title.startswith("Frieren"))
