"""TMDB 直连（视频）。"""

from __future__ import annotations

import httpx

from app.scrape.application.images import unique_https
from app.scrape.application.providers.base import MetadataProvider, ScrapeDetail, SearchHit
from app.settings.application.secrets import tmdb_api_key
from app.shared.models import WorkCatalog

_API = "https://api.themoviedb.org/3"
_IMG = "https://image.tmdb.org/t/p/w500"


class TmdbProvider(MetadataProvider):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search(self, query: str) -> list[SearchHit]:
        key = tmdb_api_key()
        if not key:
            raise RuntimeError("未配置 TMDB API Key")
        q = query.strip()
        if not q:
            return []
        client = self._client or httpx.AsyncClient(timeout=20.0)
        own = self._client is None
        try:
            hits: list[SearchHit] = []
            for media in ("movie", "tv"):
                res = await client.get(
                    f"{_API}/search/{media}",
                    params={"api_key": key, "query": q, "language": "zh-CN"},
                )
                res.raise_for_status()
                for row in (res.json().get("results") or [])[:8]:
                    ident = row.get("id")
                    if ident is None:
                        continue
                    title = (row.get("title") or row.get("name") or "").strip()
                    poster = row.get("poster_path")
                    hits.append(
                        SearchHit(
                            title=title or q,
                            key=f"tmdb:{media}:{ident}",
                            source="tmdb",
                            thumbnail_url=f"{_IMG}{poster}" if poster else None,
                            relevance=float(row.get("popularity") or 0),
                        )
                    )
            hits.sort(key=lambda h: -(h.relevance or 0))
            return hits[:10]
        finally:
            if own:
                await client.aclose()

    async def detail(self, key: str) -> ScrapeDetail:
        api_key = tmdb_api_key()
        if not api_key:
            raise RuntimeError("未配置 TMDB API Key")
        parts = key.split(":")
        if len(parts) != 3 or parts[0] != "tmdb" or parts[1] not in ("movie", "tv") or not parts[2].isdigit():
            raise RuntimeError("无效 TMDB 键")
        media, ident = parts[1], parts[2]
        client = self._client or httpx.AsyncClient(timeout=20.0)
        own = self._client is None
        try:
            res = await client.get(
                f"{_API}/{media}/{ident}",
                params={"api_key": api_key, "language": "zh-CN"},
            )
            res.raise_for_status()
            data = res.json()
            title = (data.get("title") or data.get("name") or "").strip()
            poster = data.get("poster_path")
            poster_url = f"{_IMG}{poster}" if poster else None
            covers = unique_https([poster_url])
            tags = [str(g.get("name")) for g in (data.get("genres") or []) if g.get("name")]
            catalog = WorkCatalog(
                original_title=(data.get("original_title") or data.get("original_name") or None),
                name_cn=title or None,
                date=(data.get("release_date") or data.get("first_air_date") or None),
                site_score=float(data["vote_average"]) if data.get("vote_average") is not None else None,
                image_urls=covers,
                source="tmdb",
                source_id=f"{media}:{ident}",
            )
            return ScrapeDetail(
                title=title or ident,
                synopsis=(data.get("overview") or None),
                tags=tags,
                poster_url=covers[0] if covers else None,
                cover_urls=covers,
                catalog=catalog,
                source_ref=key,
            )
        finally:
            if own:
                await client.aclose()
