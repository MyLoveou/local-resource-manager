"""通用 Open Graph：用户给出作品页面，取标题与封面。"""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urljoin

import httpx

from app.download.application.errors import DownloadError
from app.download.application.ssrf import validate_http_url
from app.scrape.application.images import public_image_url
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.shared.models import WorkCatalog

_MAX_HTML = 512 * 1024
_HEADERS = {"User-Agent": "SourceManager/0.1 (local library; metadata scrape)", "Accept": "text/html"}
_TITLE = re.compile(r"<title[^>]*>([^<]{1,300})</title>", re.I)


def page_url_or_error(raw: str) -> str:
    try:
        return validate_http_url(raw)
    except DownloadError as exc:
        text = str(exc)
        text = text.replace("下载地址", "页面链接").replace("下载", "抓取")
        raise RuntimeError(text) from exc


def parse_open_graph(html: str, page_url: str) -> tuple[str, str | None, str | None]:
    title = _meta(html, "og:title") or _tag_title(html) or page_url
    image = _meta(html, "og:image")
    if image:
        image = urljoin(page_url, unescape(image).strip())
        image = public_image_url(image)
    description = _meta(html, "og:description")
    return unescape(title).strip() or page_url, image, description


def _tag_title(html: str) -> str | None:
    found = _TITLE.search(html)
    if not found:
        return None
    text = unescape(found.group(1)).strip()
    return text or None


def _meta(html: str, prop: str) -> str | None:
    prop_q = re.escape(prop)
    patterns = (
        rf'<meta[^>]+(?:property|name)=["\']{prop_q}["\'][^>]+content=["\']([^"\']*)',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{prop_q}["\']',
    )
    for pattern in patterns:
        found = re.search(pattern, html, re.I)
        if found and found.group(1).strip():
            return unescape(found.group(1)).strip()
    return None


class OgProvider(MetadataProvider):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search(self, query: str) -> list[SearchHit]:
        page = page_url_or_error(query)
        title, image, _desc = await self._load(page)
        return [
            SearchHit(
                title=title,
                key=f"og:{page}",
                source="og",
                thumbnail_url=image,
                relevance=1.0,
            )
        ]

    async def detail(self, key: str) -> ScrapeDetail:
        prefix, _, page = key.partition(":")
        if prefix.lower() != "og" or not page:
            raise RuntimeError("无效页面键")
        title, image, desc = await self._load(page_url_or_error(page))
        covers = [image] if image else []
        return ScrapeDetail(
            title=title,
            synopsis=desc,
            tags=[],
            poster_url=image,
            cover_urls=covers,
            catalog=WorkCatalog(source="og", source_id=page, original_title=title),
            source_ref=f"og:{page}",
        )

    async def _load(self, page: str) -> tuple[str, str | None, str | None]:
        own = self._client is None
        http = self._client or httpx.AsyncClient(timeout=20.0, follow_redirects=False, headers=_HEADERS)
        try:
            current = page
            for _ in range(5):
                res = await http.get(current)
                if res.status_code in {301, 302, 303, 307, 308}:
                    loc = res.headers.get("location")
                    if not loc:
                        raise RuntimeError("跳转缺少地址")
                    current = page_url_or_error(urljoin(current, loc))
                    continue
                res.raise_for_status()
                ctype = (res.headers.get("content-type") or "").lower()
                if "html" not in ctype and "xml" not in ctype:
                    raise RuntimeError("不是网页")
                return parse_open_graph(res.text[:_MAX_HTML], str(res.url))
            raise RuntimeError("跳转次数过多")
        finally:
            if own:
                await http.aclose()
