"""蜜柑计划：番剧附加发现源。元数据仍尽量回落到 Bangumi。"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

import httpx

from app.scrape.application.images import normalize_https, unique_https
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.settings.application.secrets import mikan_base_url

_UA = {"User-Agent": "SourceManager/0.1 (local library; metadata scrape)"}
_BANGUMI_HREF = re.compile(r'href=["\']/Home/Bangumi/(\d+)["\']', re.I)
_BANGUMI_NAMED = re.compile(
    r'href=["\']/Home/Bangumi/(\d+)["\'][^>]*>([^<]{1,200})',
    re.I,
)
_OG_TITLE = re.compile(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', re.I)
_OG_IMAGE = re.compile(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', re.I)
_BGM_SUBJECT = re.compile(r"(?:bgm|bangumi)\.tv/subject/(\d+)", re.I)
_H1 = re.compile(r"<h1[^>]*>([^<]+)</h1>", re.I)


def parse_search_hits(html: str, query: str) -> list[SearchHit]:
    titles: dict[str, str] = {}
    for ident, name in _BANGUMI_NAMED.findall(html):
        text = unescape(name).strip()
        if text and ident not in titles:
            titles[ident] = text
    hits: list[SearchHit] = []
    seen: set[str] = set()
    for ident in _BANGUMI_HREF.findall(html):
        if ident in seen:
            continue
        seen.add(ident)
        hits.append(
            SearchHit(
                title=titles.get(ident) or query,
                key=f"mikan:{ident}",
                source="mikan",
                thumbnail_url=None,
                relevance=0.4,
            )
        )
        if len(hits) >= 8:
            break
    return hits


def parse_bangumi_page(html: str, ident: str, base: str) -> tuple[str, str | None, str | None]:
    """返回 title、poster_url、bangumi.tv subject id。"""
    title = ""
    og_t = _OG_TITLE.search(html)
    if og_t:
        title = unescape(og_t.group(1)).strip()
    if not title:
        h1 = _H1.search(html)
        if h1:
            title = unescape(h1.group(1)).strip()
    if not title:
        title = ident
    poster = None
    og_i = _OG_IMAGE.search(html)
    if og_i:
        poster = urljoin(base + "/", unescape(og_i.group(1)).strip())
        poster = normalize_https(poster)
    bgm = None
    found = _BGM_SUBJECT.search(html)
    if found:
        bgm = found.group(1)
    return title, poster, bgm


class MikanProvider(MetadataProvider):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    def _headers(self) -> dict[str, str]:
        return dict(_UA)

    async def search(self, query: str) -> list[SearchHit]:
        q = query.strip()
        if not q:
            return []
        base = mikan_base_url()
        client = self._client or httpx.AsyncClient(timeout=20.0, headers=self._headers(), follow_redirects=True)
        own = self._client is None
        try:
            res = await client.get(f"{base}/Home/Search", params={"searchstr": q})
            res.raise_for_status()
            return parse_search_hits(res.text, q)
        finally:
            if own:
                await client.aclose()

    async def detail(self, key: str) -> ScrapeDetail:
        parts = key.split(":")
        if len(parts) != 2 or parts[0] != "mikan" or not parts[1].isdigit():
            raise RuntimeError("无效蜜柑键")
        ident = parts[1]
        base = mikan_base_url()
        client = self._client or httpx.AsyncClient(timeout=20.0, headers=self._headers(), follow_redirects=True)
        own = self._client is None
        try:
            res = await client.get(f"{base}/Home/Bangumi/{ident}")
            res.raise_for_status()
            title, poster, bgm_id = parse_bangumi_page(res.text, ident, base)
        finally:
            if own:
                await client.aclose()
        if bgm_id:
            from app.scrape.application.providers.bangumi import BangumiProvider

            try:
                rich = await BangumiProvider(self._client).detail(f"bangumi:{bgm_id}")
                return ScrapeDetail(
                    title=rich.title or title,
                    synopsis=rich.synopsis,
                    tags=rich.tags,
                    poster_url=rich.poster_url or poster,
                    cover_urls=rich.cover_urls or unique_https([poster]),
                    catalog=rich.catalog,
                    source_ref=f"mikan:{ident};bangumi:{bgm_id}",
                )
            except Exception:
                pass
        covers = unique_https([poster])
        return ScrapeDetail(
            title=title,
            synopsis=None,
            tags=[],
            poster_url=covers[0] if covers else None,
            cover_urls=covers,
            catalog=None,
            source_ref=f"mikan:{ident}",
        )
