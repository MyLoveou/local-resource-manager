"""刮削渠道配额：前一个渠道不能把后面的结果挤出总上限。

对应线上现象：番剧只有 Bangumi 结果，蜜柑即使返回了也被截断。
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
            SearchHit(title=f"{self.name}-{index}", key=f"{self.name}:{index}", source=self.name)
            for index in range(self.count)
        ]


class _BrokenProvider:
    async def search(self, query: str) -> list[SearchHit]:
        raise TimeoutError()


class ScrapeQuotaTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_provider_cannot_crowd_out_the_second(self) -> None:
        result = await jobs_module._collect_hits(
            [_FakeProvider("bangumi", 15), _FakeProvider("mikan", 15)], "q", "q"
        )
        self.assertEqual(len(result), jobs_module._OVERALL_CAP)
        by_source = {}
        for hit in result:
            by_source[hit.source] = by_source.get(hit.source, 0) + 1
        self.assertEqual(by_source.get("bangumi"), jobs_module._PER_PROVIDER_CAP)
        self.assertEqual(by_source.get("mikan"), jobs_module._PER_PROVIDER_CAP)

    async def test_duplicate_keys_collapse(self) -> None:
        class _Dupe:
            async def search(self, query: str) -> list[SearchHit]:
                return [
                    SearchHit(title="same", key="mikan:1", source="mikan"),
                    SearchHit(title="same", key="mikan:1", source="mikan"),
                ]

        result = await jobs_module._collect_hits([_Dupe()], "q", "q")
        self.assertEqual(len(result), 1)

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
