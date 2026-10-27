"""AI 兜底：只选片段、不生成；不合法就退回规则结果。"""

from __future__ import annotations

import unittest

from app.library.application.smart_import.base import ActionContext, Suggestion
from app.library.application.smart_import.title_ai import (
    build_prompt,
    compose_title,
    parse_selection,
    refine_suggestions,
    reset_cache,
    suggest_title,
)
from app.library.domain.models import ResourceType

DBD = (
    "[DBD-Raws][异世界舅舅][01-13TV全集+特典映像][1080P][BDRip]"
    "[HEVC-10bit][简繁日双语外挂][FLAC][MKV]"
)
SEGMENTS = ["DBD-Raws", "异世界舅舅", "01-13TV全集+特典映像", "1080P"]


class PromptTests(unittest.TestCase):
    def test_segments_are_numbered(self) -> None:
        prompt = build_prompt(SEGMENTS)
        self.assertIn("0: DBD-Raws", prompt)
        self.assertIn("1: 异世界舅舅", prompt)
        self.assertIn("只输出 JSON", prompt)

    def test_known_titles_are_hints(self) -> None:
        prompt = build_prompt(SEGMENTS, ("异世界舅舅",))
        self.assertIn("异世界舅舅", prompt)

    def test_known_titles_default_to_none_marker(self) -> None:
        self.assertIn("（无）", build_prompt(SEGMENTS))


class ParseTests(unittest.TestCase):
    def test_plain_json(self) -> None:
        self.assertEqual(parse_selection('{"keep": [1]}', SEGMENTS), [1])

    def test_json_wrapped_in_prose(self) -> None:
        reply = '标题应该是：{"keep": [1, 2]} 以上。'
        self.assertEqual(parse_selection(reply, SEGMENTS), [1, 2])

    def test_out_of_range_is_rejected(self) -> None:
        self.assertIsNone(parse_selection('{"keep": [9]}', SEGMENTS))

    def test_empty_is_rejected(self) -> None:
        self.assertIsNone(parse_selection('{"keep": []}', SEGMENTS))

    def test_non_json_is_rejected(self) -> None:
        self.assertIsNone(parse_selection("就是异世界舅舅", SEGMENTS))

    def test_bool_is_rejected(self) -> None:
        self.assertIsNone(parse_selection('{"keep": [true]}', SEGMENTS))


class ComposeTests(unittest.TestCase):
    def test_single_segment(self) -> None:
        self.assertEqual(compose_title(SEGMENTS, [1]), "异世界舅舅")

    def test_cjk_adjacent_without_space(self) -> None:
        segments = ["异世界", "舅舅"]
        self.assertEqual(compose_title(segments, [0, 1]), "异世界舅舅")

    def test_latin_segments_keep_space(self) -> None:
        segments = ["Sousou", "no", "Frieren"]
        self.assertEqual(compose_title(segments, [0, 2]), "Sousou Frieren")


class _FakeComplete:
    def __init__(self, reply: str | None) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str | None:
        self.prompts.append(prompt)
        return self.reply


class SuggestTitleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        reset_cache()

    async def test_valid_selection_is_used(self) -> None:
        fake = _FakeComplete('{"keep": [1]}')
        result = await suggest_title(DBD, complete=fake)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result[0], "异世界舅舅")

    async def test_model_unavailable_returns_none(self) -> None:
        fake = _FakeComplete(None)
        self.assertIsNone(await suggest_title(DBD, complete=fake))

    async def test_suspicious_result_is_rejected(self) -> None:
        # 选了包含集数范围的片段 → 仍可疑 → 拒绝
        fake = _FakeComplete('{"keep": [1, 2]}')
        self.assertIsNone(await suggest_title(DBD, complete=fake))

    async def test_single_segment_name_is_not_worth_a_call(self) -> None:
        fake = _FakeComplete('{"keep": [0]}')
        self.assertIsNone(await suggest_title("[异世界舅舅]", complete=fake))
        self.assertEqual(fake.prompts, [])


class RefineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        reset_cache()

    def _ctx(self) -> ActionContext:
        return ActionContext(
            resource_id=1,
            type=ResourceType.ANIME,
            file_stem="[异世界舅舅]",
            dir_name=DBD,
        )

    def _rule(self, text: str) -> Suggestion:
        return Suggestion(
            field="title",
            value={"text": text},
            confidence=0.55,
            reason="去掉了 `[1080P]`；可疑残留",
            source="rule",
        )

    async def test_suspicious_suggestion_is_replaced(self) -> None:
        fake = _FakeComplete('{"keep": [1]}')
        out = await refine_suggestions(self._ctx(), [self._rule("异世界舅舅1080P")], complete=fake, enabled=True)
        self.assertEqual(out[0].value, {"text": "异世界舅舅"})
        self.assertEqual(out[0].source, "ai")
        self.assertGreater(out[0].confidence, 0.85)

    async def test_clean_suggestion_is_also_refined(self) -> None:
        # AI 为主路径：规则判不出问题的标题同样交给模型复核
        fake = _FakeComplete('{"keep": [1]}')
        out = await refine_suggestions(self._ctx(), [self._rule("异世界舅舅")], complete=fake, enabled=True)
        self.assertEqual(out[0].source, "ai")
        self.assertEqual(len(fake.prompts), 1)

    async def test_model_failure_keeps_rule_result(self) -> None:
        fake = _FakeComplete(None)
        original = self._rule("异世界舅舅1080P")
        out = await refine_suggestions(self._ctx(), [original], complete=fake, enabled=True)
        self.assertEqual(out[0], original)
