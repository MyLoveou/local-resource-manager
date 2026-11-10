"""发现层：search → 候选键；detail → 可回填字段。不含大模型。"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.library.domain.models import WorkCatalog


@dataclass(frozen=True)
class SearchHit:
    title: str
    key: str
    source: str
    thumbnail_url: str | None = None
    relevance: float | None = None


@dataclass(frozen=True)
class ScrapeDetail:
    title: str
    synopsis: str | None
    tags: list[str] = field(default_factory=list)
    poster_url: str | None = None
    cover_urls: list[str] = field(default_factory=list)
    catalog: WorkCatalog | None = None
    source_ref: str = ""


class MetadataProvider:
    async def search(self, query: str) -> list[SearchHit]:
        raise NotImplementedError

    async def detail(self, key: str) -> ScrapeDetail:
        raise NotImplementedError
