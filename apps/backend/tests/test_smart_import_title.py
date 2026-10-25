"""发布组命名清洗（S1 · smart-import）。"""
from __future__ import annotations

import unittest

from app.library.application.smart_import.title_clean import (
    clean_release_name,
    describe_removed,
)


class CleanReleaseNameTests(unittest.TestCase):
    def test_vcb_studio_release(self) -> None:
        """V1：字幕组 + 集号 + 参数全部剥掉。"""
        result = clean_release_name(
            "[VCB-Studio] Sousou no Frieren [01][Ma10p_1080p][x265_flac]"
        )
        self.assertEqual(result.title, "Sousou no Frieren")
        self.assertEqual(len(result.removed), 4)
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_lilith_raws_release(self) -> None:
        """V2：中文标题 + 多段参数 + 尾部署名号。"""
        result = clean_release_name(
            "[Lilith-Raws] 葬送的芙莉莲 - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
        )
        self.assertEqual(result.title, "葬送的芙莉莲")
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_chinese_subgroup_marker(self) -> None:
        result = clean_release_name("[桜都字幕组] 葬送的芙莉莲 第01话 [1080p]")
        self.assertEqual(result.title, "葬送的芙莉莲")

    def test_plain_chinese_with_episode(self) -> None:
        """V3：没有噪音段时只剥集号，置信度落在中间档，不会默认勾选。"""
        result = clean_release_name("夏日海边 01")
        self.assertEqual(result.title, "夏日海边")
        self.assertLess(result.confidence, 0.85)
        self.assertGreater(result.confidence, 0.0)

    def test_prefer_ep_keeps_episode(self) -> None:
        """titleWithEp 打开时保留集号。"""
        result = clean_release_name("夏日海边 01", prefer_ep=True)
        self.assertEqual(result.title, "夏日海边 01")

    def test_clean_title_yields_no_suggestion(self) -> None:
        """V12：本来就干净的名字不产生建议。"""
        result = clean_release_name("夏日海边")
        self.assertEqual(result.title, "夏日海边")
        self.assertEqual(result.removed, ())
        self.assertEqual(result.confidence, 0.0)

    def test_empty_result_falls_back_to_source(self) -> None:
        """V4：全被剥光时回退原名称，且置信度极低。"""
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

    def test_does_not_touch_non_bracket_prefix(self) -> None:
        result = clean_release_name("Frieren 葬送的芙莉莲 S01E02 1080p")
        self.assertTrue(result.title.startswith("Frieren"))

    def test_season_marker_removed(self) -> None:
        """番剧目录名带 S01 时，季号不进作品标题。"""
        result = clean_release_name("葬送的芙莉莲 S01")
        self.assertEqual(result.title, "葬送的芙莉莲")
        self.assertIn("S01", " ".join(result.removed))

    def test_season_episode_removed(self) -> None:
        result = clean_release_name("[VCB-Studio] Frieren S01E02 [1080p]")
        self.assertEqual(result.title, "Frieren")

    def test_chinese_season_and_episode_removed(self) -> None:
        result = clean_release_name("葬送的芙莉莲 第2季 第05话 [1080p]")
        self.assertEqual(result.title, "葬送的芙莉莲")
