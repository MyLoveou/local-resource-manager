"""蜜柑页面解析：解析不出标题时不能拿数字 id 顶上。

线上事故：D-fragments 导入后被改成 "273"——蜜柑详情页没解析出 og:title，
旧代码回退成 `ident`，而 ident 就是番剧 id。
"""

from __future__ import annotations

import unittest

from app.scrape.application.providers.mikan import parse_bangumi_page

BASE = "https://mikanani.example/"


class MikanParseTests(unittest.TestCase):
    def test_og_title_used(self) -> None:
        html = '<meta property="og:title" content="D-fragments" /><meta property="og:image" content="/img/a.jpg" />'
        title, poster, bgm = parse_bangumi_page(html, "273", BASE)
        self.assertEqual(title, "D-fragments")
        self.assertTrue(poster and poster.startswith("https://"))
        self.assertIsNone(bgm)

    def test_h1_used_when_no_og_title(self) -> None:
        title, _, _ = parse_bangumi_page("<h1>  D-fragments  </h1>", "273", BASE)
        self.assertEqual(title, "D-fragments")

    def test_missing_title_does_not_fall_back_to_id(self) -> None:
        title, _, _ = parse_bangumi_page("<html><body>blocked</body></html>", "273", BASE)
        self.assertEqual(title, "")

    def test_bangumi_subject_extracted(self) -> None:
        html = '<a href="https://bgm.tv/subject/12345">x</a>'
        _, _, bgm = parse_bangumi_page(html, "273", BASE)
        self.assertEqual(bgm, "12345")
