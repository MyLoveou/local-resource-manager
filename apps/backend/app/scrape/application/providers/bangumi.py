"""Bangumi 直连（番剧）。"""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.scrape.application.images import unique_https
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.settings.application.secrets import bangumi_token
from app.shared.models import WorkCatalog

_UA = {"User-Agent": "SourceManager/0.1 (local library; metadata scrape)"}


def _aliases_from_infobox(infobox: list[object]) -> list[str]:
    names: list[str] = []
    for item in infobox:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        if key not in ("别名", "英文名", "日文名"):
            continue
        value = item.get("value")
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
        elif isinstance(value, list):
            for piece in value:
                if isinstance(piece, dict) and piece.get("v"):
                    names.append(str(piece["v"]).strip())
                elif isinstance(piece, str) and piece.strip():
                    names.append(piece.strip())
    return [n for n in names if n]


class BangumiProvider(MetadataProvider):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    def _headers(self) -> dict[str, str]:
        headers = dict(_UA)
        token = bangumi_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def search(self, query: str) -> list[SearchHit]:
        q = query.strip()
        if not q:
            return []
        client = self._client or httpx.AsyncClient(timeout=20.0, headers=self._headers())
        own = self._client is None
        try:
            url = f"https://api.bgm.tv/search/subject/{quote(q)}"
            res = await client.get(url, params={"type": 2, "responseGroup": "small", "max_results": 10})
            res.raise_for_status()
            payload = res.json()
            rows = payload.get("list") if isinstance(payload, dict) else payload
            hits: list[SearchHit] = []
            for row in rows or []:
                ident = row.get("id")
                if ident is None:
                    continue
                name = (row.get("name_cn") or row.get("name") or "").strip()
                images = row.get("images") or {}
                thumb = unique_https(
                    [images.get("large"), images.get("common"), images.get("small")]
                )
                hits.append(
                    SearchHit(
                        title=name or q,
                        key=f"bangumi:{ident}",
                        source="bangumi",
                        thumbnail_url=thumb[0] if thumb else None,
                        relevance=float(row.get("id") or 0),
                    )
                )
            return hits[:10]
        finally:
            if own:
                await client.aclose()

    async def detail(self, key: str) -> ScrapeDetail:
        parts = key.split(":")
        if len(parts) != 2 or parts[0] != "bangumi" or not parts[1].isdigit():
            raise RuntimeError("无效 Bangumi 键")
        ident = parts[1]
        client = self._client or httpx.AsyncClient(timeout=20.0, headers=self._headers())
        own = self._client is None
        try:
            res = await client.get(f"https://api.bgm.tv/v0/subjects/{ident}")
            res.raise_for_status()
            data = res.json()
            title = (data.get("name_cn") or data.get("name") or ident).strip()
            tags = [str(t.get("name")) for t in (data.get("tags") or []) if t.get("name")][:20]
            images = data.get("images") or {}
            covers = unique_https(
                [
                    images.get("large"),
                    images.get("common"),
                    images.get("medium"),
                    images.get("small"),
                ]
            )
            rating = data.get("rating") or {}
            score = rating.get("score")
            infobox = [row for row in (data.get("infobox") or []) if isinstance(row, dict)]
            catalog = WorkCatalog(
                original_title=(data.get("name") or None),
                name_cn=(data.get("name_cn") or None),
                date=(data.get("date") or None),
                platform=(data.get("platform") or None),
                eps=data.get("eps"),
                total_episodes=data.get("total_episodes"),
                site_score=float(score) if score is not None else None,
                infobox=infobox,
                aliases=_aliases_from_infobox(infobox),
                image_urls=covers,
                source="bangumi",
                source_id=str(ident),
            )
            return ScrapeDetail(
                title=title,
                synopsis=(data.get("summary") or None),
                tags=tags,
                poster_url=covers[0] if covers else None,
                cover_urls=covers,
                catalog=catalog,
                source_ref=key,
            )
        finally:
            if own:
                await client.aclose()
