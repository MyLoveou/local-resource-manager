"""B 站公开稿件：BV/av 直取为主，关键词尽力。无登录、无 Cookie。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from app.scrape.application.images import normalize_https, unique_https
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.shared.models import WorkCatalog

_API = "https://api.bilibili.com/x/web-interface/view"
_SEARCH = "https://api.bilibili.com/x/web-interface/search/type"
_BV = re.compile(r"BV1[0-9A-Za-z]{9}", re.I)
_AV = re.compile(r"(?<![A-Za-z0-9])av(\d{1,12})(?![A-Za-z0-9])", re.I)
_SAFE_HOSTS = frozenset(
    {
        "www.bilibili.com",
        "bilibili.com",
        "m.bilibili.com",
        "b23.tv",
        "www.b23.tv",
    }
)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SourceManager/0.1",
    "Referer": "https://www.bilibili.com",
}


def _norm_bvid(raw: str) -> str:
    return "BV" + raw[2:] if raw.lower().startswith("bv") else raw


def extract_ids(text: str) -> list[tuple[str, str]]:
    """从文本抽出 (kind, value)，kind 为 bvid 或 aid；保序去重，最多 3 个。"""
    if not text:
        return []
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in _BV.finditer(text):
        bvid = _norm_bvid(match.group(0))
        key = "bvid:" + bvid.upper()
        if key in seen:
            continue
        seen.add(key)
        found.append(("bvid", bvid))
        if len(found) >= 3:
            return found
    for match in _AV.finditer(text):
        aid = match.group(1)
        key = "aid:" + aid
        if key in seen:
            continue
        seen.add(key)
        found.append(("aid", aid))
        if len(found) >= 3:
            break
    return found


def looks_like_url(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("http://") or stripped.startswith("https://")


async def resolve_query_ids(text: str, client: httpx.AsyncClient | None = None) -> list[tuple[str, str]]:
    ids = extract_ids(text)
    if ids or not looks_like_url(text):
        return ids
    parsed = urlparse(text.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in _SAFE_HOSTS:
        return []
    own = client is None
    http = client or httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=_HEADERS)
    try:
        res = await http.get(text.strip())
        final = str(res.url)
        final_host = (urlparse(final).hostname or "").lower().rstrip(".")
        if final_host not in _SAFE_HOSTS:
            return []
        return extract_ids(final)
    except httpx.HTTPError:
        return []
    finally:
        if own:
            await http.aclose()


def _hit_from_view(data: dict) -> SearchHit | None:
    bvid = str(data.get("bvid") or "").strip()
    title = str(data.get("title") or "").strip()
    if not bvid:
        return None
    pic = normalize_https(str(data.get("pic") or "") or None)
    return SearchHit(
        title=title or bvid,
        key=f"bilibili:{bvid}",
        source="bilibili",
        thumbnail_url=pic,
        relevance=1.0,
    )


def _detail_from_view(data: dict) -> ScrapeDetail:
    bvid = str(data.get("bvid") or "").strip()
    title = str(data.get("title") or "").strip() or bvid
    desc = str(data.get("desc") or "").strip() or None
    pic = normalize_https(str(data.get("pic") or "") or None)
    covers = unique_https([pic])
    tname = str(data.get("tname") or "").strip()
    owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
    up = str(owner.get("name") or "").strip()
    pubdate = data.get("pubdate")
    date = None
    if isinstance(pubdate, (int, float)) and pubdate > 0:
        date = datetime.fromtimestamp(int(pubdate), tz=timezone.utc).date().isoformat()
    infobox: list[dict] = []
    if up:
        infobox.append({"key": "UP主", "value": up})
    if tname:
        infobox.append({"key": "分区", "value": tname})
    aid = data.get("aid")
    if aid is not None:
        infobox.append({"key": "aid", "value": str(aid)})
    catalog = WorkCatalog(
        original_title=title,
        date=date,
        platform="Bilibili",
        infobox=infobox,
        image_urls=covers,
        source="bilibili",
        source_id=bvid,
    )
    return ScrapeDetail(
        title=title,
        synopsis=desc,
        tags=[tname] if tname else [],
        poster_url=covers[0] if covers else None,
        cover_urls=covers,
        catalog=catalog,
        source_ref=f"bilibili:{bvid}",
    )


class BilibiliProvider(MetadataProvider):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search(self, query: str) -> list[SearchHit]:
        q = (query or "").strip()
        if not q:
            return []
        ids = extract_ids(q)
        if ids:
            hits: list[SearchHit] = []
            for kind, value in ids[:3]:
                try:
                    data = await self._view(
                        bvid=value if kind == "bvid" else None,
                        aid=value if kind == "aid" else None,
                    )
                except Exception:
                    continue
                hit = _hit_from_view(data)
                if hit is not None:
                    hits.append(hit)
            return hits
        return await self._keyword_search(q)

    async def detail(self, key: str) -> ScrapeDetail:
        prefix, _, ident = key.partition(":")
        if prefix.lower() != "bilibili" or not ident:
            raise RuntimeError("无效 B 站键")
        if ident.lower().startswith("av") and ident[2:].isdigit():
            data = await self._view(aid=ident[2:])
        else:
            data = await self._view(bvid=ident)
        return _detail_from_view(data)

    async def _view(self, *, bvid: str | None = None, aid: str | None = None) -> dict:
        params: dict[str, str] = {}
        if bvid:
            params["bvid"] = bvid
        elif aid:
            params["aid"] = aid
        else:
            raise RuntimeError("缺少稿件 id")
        client = self._client or httpx.AsyncClient(timeout=20.0, headers=_HEADERS)
        own = self._client is None
        try:
            res = await client.get(_API, params=params)
            res.raise_for_status()
            payload = res.json()
            if int(payload.get("code") or 0) != 0:
                raise RuntimeError(str(payload.get("message") or "稿件不存在"))
            data = payload.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("稿件数据无效")
            return data
        finally:
            if own:
                await client.aclose()

    async def _keyword_search(self, keyword: str) -> list[SearchHit]:
        client = self._client or httpx.AsyncClient(timeout=20.0, headers=_HEADERS)
        own = self._client is None
        try:
            res = await client.get(
                _SEARCH,
                params={"search_type": "video", "keyword": keyword},
            )
            res.raise_for_status()
            payload = res.json()
            if int(payload.get("code") or 0) != 0:
                return []
            result = payload.get("data") or {}
            rows = result.get("result") if isinstance(result, dict) else None
            if not isinstance(rows, list):
                return []
            hits: list[SearchHit] = []
            for row in rows[:8]:
                if not isinstance(row, dict):
                    continue
                bvid = str(row.get("bvid") or "").strip()
                if not bvid:
                    continue
                title = re.sub(r"<[^>]+>", "", str(row.get("title") or "")).strip()
                pic = normalize_https(str(row.get("pic") or "") or None)
                hits.append(
                    SearchHit(
                        title=title or bvid,
                        key=f"bilibili:{bvid}",
                        source="bilibili",
                        thumbnail_url=pic,
                        relevance=0.5,
                    )
                )
            return hits
        except Exception:
            return []
        finally:
            if own:
                await client.aclose()
