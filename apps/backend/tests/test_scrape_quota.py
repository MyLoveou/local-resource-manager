"""刮削渠道互相独立：谁结果多都不影响别人，也不做跨渠道去重。

线上问题：番剧只看到 Bangumi 的结果。原因是所有渠道的命中被摊进同一个
列表、共用一个 20 条上限，先返回的渠道把后面的挤掉了。
"""

from __future__ import annotations

import unittest

from app.scrape.application import jobs as jobs_module
from app.scrape.application.providers.base import SearchHit


class _FakeProvider:
    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count

    async def search(self, query: str) -> list[SearchHit]:
        return [
            SearchHit(title=f"{self.name}-{i}", key=f"{self.name}:{i}", source=self.name)
            for i in range(self.count)
        ]


class _BrokenProvider:
    async def search(self, query: str) -> list[SearchHit]:
        raise TimeoutError()


class _DupeProvider:
    async def search(self, query: str) -> list[SearchHit]:
        return [
            SearchHit(title="same", key="mikan:1", source="mikan"),
            SearchHit(title="same again", key="mikan:1", source="mikan"),
        ]


class ScrapeQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_channels_do_not_crowd_each_other(self) -> None:
        """两个渠道都返回满额时，各拿各的，谁都不少。"""
        result = await jobs_module._collect_hits(
            [_FakeProvider("bangumi", 30), _FakeProvider("mikan", 30)], "q", "q"
        )
        by_source: dict[str, int] = {}
        for hit in result:
            by_source[hit.source] = by_source.get(hit.source, 0) + 1
        self.assertEqual(by_source.get("bangumi"), jobs_module._PER_PROVIDER_CAP)
        self.assertEqual(by_source.get("mikan"), jobs_module._PER_PROVIDER_CAP)
        self.assertEqual(len(result), jobs_module._PER_PROVIDER_CAP * 2)

    async def test_duplicate_keys_collapse_within_one_channel(self) -> None:
        result = await jobs_module._collect_hits([_DupeProvider()], "q", "q")
        self.assertEqual(len(result), 1)

    async def test_same_key_from_two_channels_is_kept_for_both(self) -> None:
        class _SameKey:
            def __init__(self, source: str) -> None:
                self.source = source

            async def search(self, query: str) -> list[SearchHit]:
                return [SearchHit(title="t", key="shared:1", source=self.source)]

        result = await jobs_module._collect_hits([_SameKey("a"), _SameKey("b")], "q", "q")
        self.assertEqual(sorted(hit.source for hit in result), ["a", "b"])

    async def test_failure_of_one_provider_keeps_the_other(self) -> None:
        result = await jobs_module._collect_hits(
            [_BrokenProvider(), _FakeProvider("mikan", 3)], "q", "q"
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].source, "mikan")

    async def test_all_failures_raise_with_provider_name(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            await jobs_module._collect_hits([_BrokenProvider()], "q", "q")
        self.assertIn("_BrokenProvider", str(ctx.exception))
        self.assertIn("TimeoutError", str(ctx.exception))
