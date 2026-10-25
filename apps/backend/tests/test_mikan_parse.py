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

    def test_attribute_order_does_not_matter(self) -> None:
        """content 写在 property 前面也必须解析出来。"""
        props_first = (
            '<meta property="og:title" content="D-fragments">'
            '<meta property="og:image" content="https://x/a.jpg">'
        )
        content_first = (
            '<meta content="D-fragments" property="og:title">'
            '<meta content="https://x/a.jpg" property="og:image">'
        )
        for html in (props_first, content_first):
            title, poster, _ = parse_bangumi_page(html, "273", BASE)
            self.assertEqual(title, "D-fragments")
            self.assertEqual(poster, "https://x/a.jpg")

    def test_single_quoted_attributes(self) -> None:
        html = "<meta content='D-fragments' property='og:title'>"
        title, _, _ = parse_bangumi_page(html, "273", BASE)
        self.assertEqual(title, "D-fragments")
