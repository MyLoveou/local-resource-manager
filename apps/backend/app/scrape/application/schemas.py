"""刮削 API DTO。"""

from pydantic import Field

from app.scrape.domain.models import Candidate, ScrapeJob
from app.shared.models import ApiModel, StrictApiModel
from app.library.domain.models import WorkCatalog


class ScrapeJobCreate(StrictApiModel):
    resource_id: int
    query: str | None = None


class ScrapeSelect(StrictApiModel):
    candidate_id: int
    # 指定时只写这一季的元数据，不覆盖整个资源
    season: int | None = None
    cover_url: str | None = None
    apply_title: bool = True
    apply_synopsis: bool = True
    apply_author: bool = True
    apply_tags: bool = True
    apply_catalog: bool = True
    apply_cover: bool = True
    replace_user_cover: bool = False


class ScrapeCurrent(ApiModel):
    title: str = ""
    synopsis: str | None = None
    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    catalog_summary: str | None = None


class ScrapePreview(ApiModel):
    title: str
    synopsis: str | None = None
    author: str | None = None
    tags: list[str]
    cover_urls: list[str]
    catalog: WorkCatalog | None = None
    catalog_summary: str | None = None
    source_ref: str = ""
    user_cover_locked: bool = False
    current: ScrapeCurrent = Field(default_factory=ScrapeCurrent)


class ScrapeJobOut(ScrapeJob):
    pass


class CandidateOut(Candidate):
    pass
