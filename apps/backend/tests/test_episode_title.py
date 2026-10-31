"""每集标题解析：抽不到就留空，不能拿作品名充数。"""

from __future__ import annotations

import unittest

from app.library.application.episode_title import episode_title_from_stem


class EpisodeTitleTests(unittest.TestCase):
    def test_title_after_episode_number(self) -> None:
        self.assertEqual(
            episode_title_from_stem("[Group] Show - 03 孤独的转校生 [1080p].mkv", "Show"),
            "孤独的转校生",
        )

    def test_sxxexx_form(self) -> None:
        self.assertEqual(
            episode_title_from_stem("[Group] Show S01E05 The Long Night [1080p]", "Show"),
            "The Long Night",
        )

    def test_chinese_episode_marker(self) -> None:
        self.assertEqual(episode_title_from_stem("Show - 第3话 约定", "Show"), "约定")

    def test_series_name_alone_is_not_a_title(self) -> None:
        self.assertIsNone(
            episode_title_from_stem(
                "[VCB-Studio] Kami nomi zo Shiru Sekai [01][Ma10p_1080p][x265_flac].mkv",
                "Kami nomi zo Shiru Sekai",
            )
        )

    def test_bare_number_is_not_a_title(self) -> None:
        self.assertIsNone(episode_title_from_stem("[Group] Show [07]", "Show"))

    def test_random_file_has_no_title(self) -> None:
        self.assertIsNone(episode_title_from_stem("random file.mkv", None))

    def test_codec_noise_is_stripped(self) -> None:
        title = episode_title_from_stem(
            "[Group] Show - 02 相遇 [1080p][x265_flac][CHS].mkv", "Show"
        )
        self.assertEqual(title, "相遇")
