"""确认后按勾选字段回填；不改用户评价。"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from app.library.application.covers.attach import attach_cover_image
from app.library.application.covers.origin import COVER_ORIGIN_SCRAPED, is_user_locked
from app.library.application.packages import layout_for
from app.library.application.packages.resource_package import ResourcePackage, default_library_store
from app.library.infrastructure.repositories import ResourceRepository
from app.scrape.application.images import fetch_poster_bytes, normalize_https, unique_https
from app.scrape.application.providers.base import ScrapeDetail
from app.shared.config import settings
from app.shared.fs.file_ops import FileOps
from app.library.domain.models import (
    Resource,
    WorkCatalog,
)


def _allowed_cover_set(detail: ScrapeDetail) -> set[str]:
    return set(unique_https([*detail.cover_urls, detail.poster_url]))


def up_from_catalog(catalog: WorkCatalog | None) -> str | None:
    if catalog is None:
        return None
    for row in catalog.infobox:
        if str(row.get("key") or "") != "UP主":
            continue
        value = row.get("value")
        text = str(value).strip() if value is not None else ""
        if text:
            return text
    return None


def catalog_summary(catalog: WorkCatalog | None) -> str | None:
    if catalog is None:
        return None
    return catalog.original_title or catalog.name_cn or catalog.date or "已有档案"


async def apply_scrape_detail(
    resources: ResourceRepository,
    resource: Resource,
    detail: ScrapeDetail,
    *,
    cover_url: str | None = None,
    apply_title: bool = True,
    apply_synopsis: bool = True,
    apply_author: bool = True,
    apply_tags: bool = True,
    apply_catalog: bool = True,
    apply_cover: bool = True,
    replace_user_cover: bool = False,
    season: int | None = None,
) -> None:
    if resource.id is None:
        return
    if season is not None:
        await _apply_to_season(resources, resource.id, season, detail, apply_title, apply_catalog)
        return
    if not any((apply_title, apply_synopsis, apply_author, apply_tags, apply_catalog, apply_cover)):
        raise RuntimeError("至少选择一项写入")
    poster: str | None = None
    payload: tuple[bytes, str] | None = None
    if apply_cover:
        poster = normalize_https(cover_url) or normalize_https(detail.poster_url)
        if poster:
            allowed = _allowed_cover_set(detail)
            if poster not in allowed:
                raise RuntimeError("封面不在候选中")
            if not (is_user_locked(resource) and not replace_user_cover):
                payload = await fetch_poster_bytes(poster)
    if apply_title and detail.title.strip():
        resource.title = detail.title
    if apply_synopsis:
        resource.synopsis = detail.synopsis
    if apply_catalog and detail.catalog:
        resource.catalog = detail.catalog
    if apply_author:
        up = up_from_catalog(detail.catalog)
        if up:
            resource.author = up
    resource.last_scraped_at = datetime.now()
    resource.scraped_source = detail.source_ref
    resource._touch()
    await resources.update(resource.id, resource, commit=False)
    if apply_tags and detail.tags:
        await resources.add_tags_union(resource.id, detail.tags, commit=False)
    await resources.commit()
    if payload is None:
        return
    tmp_path: Path | None = None
    try:
        suffix = ".jpg"
        mime = payload[1]
        if mime == "image/png":
            suffix = ".png"
        elif mime == "image/webp":
            suffix = ".webp"
        handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        handle.write(payload[0])
        handle.close()
        tmp_path = Path(handle.name)
        layout = layout_for(resource.type)
        package = ResourcePackage(
            default_library_store(settings.db_path),
            resource.type,
            resource.id,
            FileOps(),
            cover_falls_back_to_primary=bool(layout and layout.cover_falls_back_to_primary),
        )
        fresh = await resources.get(resource.id)
        if fresh is None:
            return
        await attach_cover_image(
            resources,
            fresh,
            package,
            tmp_path,
            COVER_ORIGIN_SCRAPED,
            honor_user_lock=not replace_user_cover,
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


async def _apply_to_season(
    resources: ResourceRepository,
    resource_id: int,
    season: int,
    detail: ScrapeDetail,
    apply_title: bool,
    apply_catalog: bool,
) -> None:
    """把元数据写到某一季，而不是整个资源。"""
    session = resources._session
    from sqlalchemy import text as sql_text

    catalog = detail.catalog
    payload = catalog.model_dump_json() if (apply_catalog and catalog is not None) else None
    title = detail.title if apply_title else None
    await session.execute(
        sql_text(
            "UPDATE seasons SET catalog_json = COALESCE(:catalog, catalog_json), "
            "title = COALESCE(:title, title) "
            "WHERE resource_id = :rid AND season_number = :season"
        ),
        {"catalog": payload, "title": title, "rid": resource_id, "season": season},
    )
    await session.commit()
