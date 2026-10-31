"""作品标题清洗：规则覆盖方括号噪声，模型兜底点分命名。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.series_title import (
    parse_title_reply,
    rule_title,
    series_title,
    title_from_path,
)


class RuleTitleTests(unittest.TestCase):
    def test_bracket_group_is_removed(self) -> None:
        self.assertEqual(
            rule_title("[VCB-Studio] Kami nomi zo Shiru Sekai"), "Kami nomi zo Shiru Sekai"
        )

    def test_extra_tokens_removed(self) -> None:
        self.assertEqual(
            rule_title("[VCB-Studio] Kami nomi zo Shiru Sekai Megami Hen [Ma10p_1080p]"),
            "Kami nomi zo Shiru Sekai Megami Hen",
        )

    def test_dotted_release_name(self) -> None:
        self.assertEqual(rule_title("Show.S01.1080p.BluRay.x265"), "Show")

    def test_chinese_season_kept(self) -> None:
        # 中文季名是作品名的一部分，不剥
        self.assertEqual(rule_title("进击的巨人 第二季 [1080p]"), "进击的巨人 第二季")

    def test_plain_name_untouched(self) -> None:
        self.assertEqual(rule_title("Normal Show"), "Normal Show")

    def test_title_from_path_uses_stem_for_files(self) -> None:
        self.assertEqual(
            title_from_path(Path("[Group] Movie [1080p].mkv")),
            "Movie",
        )


class ReplyParseTests(unittest.TestCase):
    def test_strips_quotes_and_code_fence(self) -> None:
        self.assertEqual(parse_title_reply('```\n"作品名"\n```'), "作品名")

    def test_ignores_blank_and_bullets(self) -> None:
        self.assertEqual(parse_title_reply("\n- 作品名\n"), "作品名")

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(parse_title_reply("   \n\n"))


class _Fake:
    def __init__(self, reply: str | None) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str | None:
        self.prompts.append(prompt)
        return self.reply


class SeriesTitleTests(unittest.IsolatedAsyncioTestCase):
    async def test_rule_only_without_model(self) -> None:
        self.assertEqual(
            await series_title("[VCB-Studio] Sekai"), "Sekai"
        )

    async def test_model_result_wins(self) -> None:
        fake = _Fake("世界")
        self.assertEqual(await series_title("Sekai 2nd Season", complete=fake), "世界")
        self.assertIn("Sekai 2nd Season", fake.prompts[0])

    async def test_model_failure_falls_back(self) -> None:
        self.assertEqual(
            await series_title("[VCB-Studio] Sekai", complete=_Fake(None)), "Sekai"
        )

    async def test_model_echoing_raw_name_falls_back(self) -> None:
        raw = "[VCB-Studio] Sekai"
        self.assertEqual(await series_title(raw, complete=_Fake(raw)), "Sekai")
