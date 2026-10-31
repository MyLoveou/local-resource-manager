"""AI 结构拆分：模型只判断特典，编号由规则解析。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.library.application.series_plan_ai import (
    CHUNK_SIZE,
    build_plan,
    build_prompt,
    build_title_prompt,
    clean_titles,
    parse_indices,
    parse_titles,
    plan_with_ai,
)

MAIN = "[VCB-Studio] Sekai [{:02d}][1080p].mkv"
OVA = "[VCB-Studio] Sekai Megami Hen [{:02d}][1080p].mkv"


def _videos(root: Path, main_count: int = 3, ova_count: int = 2) -> list[Path]:
    for number in range(1, main_count + 1):
        (root / MAIN.format(number)).write_bytes(b"")
    for number in range(1, ova_count + 1):
        (root / OVA.format(number)).write_bytes(b"")
    return sorted(root.glob("*.mkv"))


class _Fake:
    def __init__(self, replies: list[str] | str) -> None:
        self.replies = replies if isinstance(replies, list) else [replies]
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str | None:
        self.prompts.append(prompt)
        index = min(len(self.prompts) - 1, len(self.replies) - 1)
        return self.replies[index]


class ParseTests(unittest.TestCase):
    def test_number_list(self) -> None:
        self.assertEqual(parse_indices("2,5,7", 10), {2, 5, 7})

    def test_none_means_empty(self) -> None:
        self.assertEqual(parse_indices("none", 10), set())

    def test_out_of_range_is_filtered(self) -> None:
        self.assertEqual(parse_indices("1, 99", 10), {1})

    def test_garbage_is_rejected(self) -> None:
        self.assertIsNone(parse_indices("我不确定", 10))
        self.assertIsNone(parse_indices("", 10))

    def test_prompt_lists_every_file(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        videos = _videos(root)
        prompt = build_prompt(videos)
        self.assertIn("1: ", prompt)
        self.assertIn("Sekai", prompt)
        self.assertIn("只输出这些文件的编号", prompt)


class BuildPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.videos = _videos(self.root, main_count=3, ova_count=2)

    def _extras(self) -> set[str]:
        return {path.as_posix() for path in self.videos if "Megami" in path.name}

    def test_ai_extras_become_extras(self) -> None:
        plan = build_plan(self.root, self.videos, self._extras())
        episodes = [item for item in plan.items if item.kind == "episode"]
        extras = [item for item in plan.items if item.kind == "extra"]
        self.assertEqual(len(episodes), 3)
        self.assertEqual(len(extras), 2)
        self.assertTrue(plan.message.startswith("AI 识别"))

    def test_numbering_comes_from_filenames(self) -> None:
        plan = build_plan(self.root, self.videos, self._extras())
        numbers = sorted(item.episode for item in plan.items if item.kind == "episode")
        self.assertEqual(numbers, [1, 2, 3])

    def test_collision_becomes_extra(self) -> None:
        """模型漏判时同一集号撞车：后来的那个归特典，而不是整单失败。"""
        plan = build_plan(self.root, self.videos, set())
        episodes = [item for item in plan.items if item.kind == "episode"]
        extras = [item for item in plan.items if item.kind == "extra"]
        self.assertEqual(len(episodes), 3)
        self.assertEqual(len(extras), 2)


class PlanWithAITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.videos = _videos(self.root, main_count=3, ova_count=2)

    async def test_uses_model_indices(self) -> None:
        plan = await plan_with_ai(self.root, self.videos, complete=_Fake("4,5"))
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(len([i for i in plan.items if i.kind == "extra"]), 2)
        self.assertEqual(len([i for i in plan.items if i.kind == "episode"]), 3)

    async def test_none_reply_keeps_all_episodes(self) -> None:
        plan = await plan_with_ai(self.root, self.videos, complete=_Fake("none"))
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(len([i for i in plan.items if i.kind == "episode"]), 3)

    async def test_unparsable_reply_returns_none(self) -> None:
        self.assertIsNone(await plan_with_ai(self.root, self.videos, complete=_Fake("不知道")))

    async def test_model_failure_returns_none(self) -> None:
        self.assertIsNone(await plan_with_ai(self.root, self.videos, complete=_Fake(None)))

    async def test_single_file_skips_model(self) -> None:
        fake = _Fake("1")
        self.assertIsNone(await plan_with_ai(self.root, self.videos[:1], complete=fake))
        self.assertEqual(fake.prompts, [])

    async def test_large_folder_is_chunked(self) -> None:
        big = tempfile.TemporaryDirectory()
        self.addCleanup(big.cleanup)
        root = Path(big.name)
        videos = _videos(root, main_count=CHUNK_SIZE + 5, ova_count=0)
        fake = _Fake(["none"] * 5)
        plan = await plan_with_ai(root, videos, complete=fake)
        self.assertIsNotNone(plan)
        self.assertEqual(len(fake.prompts), 2)


class TitleTests(unittest.TestCase):
    def test_parse_titles_requires_full_coverage(self) -> None:
        self.assertEqual(parse_titles("1|特典甲\n2|特典乙", 2), {1: "特典甲", 2: "特典乙"})
        self.assertIsNone(parse_titles("1|特典甲", 2))

    def test_prompt_mentions_cleaning(self) -> None:
        prompt = build_title_prompt([Path("x.mkv")])
        self.assertIn("清洗", prompt)
        self.assertIn("编号|清洗后的名字", prompt)


class CleanTitlesTests(unittest.IsolatedAsyncioTestCase):
    async def test_titles_are_used(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        videos = _videos(root, main_count=2, ova_count=2)
        extras = [path for path in videos if "Megami" in path.name]
        fake = _Fake("1|女神篇 第一话\n2|女神篇 第二话")
        titles = await clean_titles(fake, extras)
        self.assertEqual(len(titles), 2)
        self.assertIn("女神篇 第一话", titles.values())

    async def test_failure_returns_empty(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        extras = [path for path in _videos(root) if "Megami" in path.name]
        self.assertEqual(await clean_titles(_Fake("不知道"), extras), {})


class PlanUsesAITitlesTests(unittest.IsolatedAsyncioTestCase):
    async def test_extra_title_comes_from_model(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        videos = _videos(root, main_count=2, ova_count=2)
        fake = _Fake(["3,4", "1|女神篇 上\n2|女神篇 下"])
        plan = await plan_with_ai(root, videos, complete=fake)
        self.assertIsNotNone(plan)
        assert plan is not None
        titles = [item.title for item in plan.items if item.kind == "extra"]
        self.assertIn("女神篇 上", titles)

class TitleDegradeTests(unittest.IsolatedAsyncioTestCase):
    """模型把两个文件清洗成同一个名字时，退回规则名而不是用重复结果。"""

    async def test_duplicate_titles_fall_back(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        videos = _videos(root, main_count=2, ova_count=2)
        fake = _Fake(["3,4", "1|同一名字\n2|同一名字"])
        plan = await plan_with_ai(root, videos, complete=fake)
        self.assertIsNotNone(plan)
        assert plan is not None
        titles = [item.title for item in plan.items if item.kind == "extra"]
        self.assertEqual(len(set(titles)), 2)