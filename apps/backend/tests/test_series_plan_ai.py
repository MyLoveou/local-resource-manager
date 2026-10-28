"""AI 主导结构拆分：校验严格到"一条不合法就整份丢弃"。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.library.application.series_plan_ai import (
    build_prompt,
    parse_reply,
    plan_with_ai,
    to_plan,
)

S1 = "[VCB-Studio] Sekai [{:02d}][1080p].mkv"
S2 = "[VCB-Studio] Sekai II [{:02d}][1080p].mkv"
IDOL = "Sekai 4-nin to Idol.mkv"
GNCA = "GNCA-021002.mkv"


def _videos(root: Path) -> list[Path]:
    names = [S1.format(i) for i in range(1, 4)] + [S2.format(i) for i in range(1, 3)]
    names += [IDOL, GNCA]
    for name in names:
        (root / name).write_bytes(b"")
    return sorted(root.glob("*.mkv"))


GOOD = {
    "files": [
        {"name": "[VCB-Studio] Sekai [01][1080p]", "kind": "episode", "season": 1, "episode": 1},
        {"name": "[VCB-Studio] Sekai [02][1080p]", "kind": "episode", "season": 1, "episode": 2},
        {"name": "[VCB-Studio] Sekai [03][1080p]", "kind": "episode", "season": 1, "episode": 3},
        {"name": "[VCB-Studio] Sekai II [01][1080p]", "kind": "episode", "season": 2, "episode": 1},
        {"name": "[VCB-Studio] Sekai II [02][1080p]", "kind": "episode", "season": 2, "episode": 2},
        {"name": "Sekai 4-nin to Idol", "kind": "extra", "title": "特典 4-nin to Idol"},
        {"name": "GNCA-021002", "kind": "extra"},
    ]
}


class ParseTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.videos = _videos(self.root)

    def _parse(self, payload) -> object:
        return parse_reply(json.dumps(payload, ensure_ascii=False), self.videos)

    def test_good_reply_is_accepted(self) -> None:
        items = self._parse(GOOD)
        self.assertIsNotNone(items)
        kinds = {item.name: item.kind for item in items}
        self.assertEqual(kinds["Sekai 4-nin to Idol"], "extra")
        self.assertEqual(kinds["[VCB-Studio] Sekai II [01][1080p]"], "episode")

    def test_duplicate_episode_is_rejected(self) -> None:
        payload = json.loads(json.dumps(GOOD))
        payload["files"][1]["season"], payload["files"][1]["episode"] = 1, 1
        self.assertIsNone(self._parse(payload))

    def test_missing_file_is_rejected(self) -> None:
        payload = json.loads(json.dumps(GOOD))
        payload["files"].pop()
        self.assertIsNone(self._parse(payload))

    def test_unknown_name_is_rejected(self) -> None:
        payload = json.loads(json.dumps(GOOD))
        payload["files"].append({"name": "ghost", "kind": "extra"})
        self.assertIsNone(self._parse(payload))

    def test_out_of_range_is_rejected(self) -> None:
        payload = json.loads(json.dumps(GOOD))
        payload["files"][0]["episode"] = 0
        self.assertIsNone(self._parse(payload))

    def test_garbage_is_rejected(self) -> None:
        self.assertIsNone(parse_reply("我不确定", self.videos))
        self.assertIsNone(parse_reply("", self.videos))

    def test_fenced_json_is_tolerated(self) -> None:
        reply = "```json\n" + json.dumps(GOOD, ensure_ascii=False) + "\n```"
        self.assertIsNotNone(parse_reply(reply, self.videos))

    def test_plan_paths(self) -> None:
        items = self._parse(GOOD)
        assert items is not None
        plan = to_plan(self.root, self.videos, items)
        dests = {item.dest_rel for item in plan.items}
        self.assertIn("seasons/02/S02E01.mkv", dests)
        self.assertIn("extras/Sekai 4-nin to Idol.mkv", dests)
        self.assertIn("AI 识别", plan.message)


class _Fake:
    def __init__(self, reply: str | None) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str | None:
        self.prompts.append(prompt)
        return self.reply


class PlanWithAITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.videos = _videos(self.root)

    async def test_ai_plan_is_used(self) -> None:
        plan = await plan_with_ai(self.root, self.videos, complete=_Fake(json.dumps(GOOD)))
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertTrue(plan.ok)
        episodes = [item for item in plan.items if item.kind == "episode"]
        self.assertEqual(sorted({item.season for item in episodes}), [1, 2])

    async def test_model_unavailable_returns_none(self) -> None:
        self.assertIsNone(await plan_with_ai(self.root, self.videos, complete=_Fake(None)))

    async def test_single_file_skips_model(self) -> None:
        fake = _Fake(json.dumps(GOOD))
        one = [self.videos[0]]
        self.assertIsNone(await plan_with_ai(self.root, one, complete=fake))
        self.assertEqual(fake.prompts, [])

    def test_prompt_lists_files(self) -> None:
        prompt = build_prompt(self.videos)
        self.assertIn("Sekai II", prompt)
        self.assertIn("不要输出解释", prompt)
