"""Shared resource ORM-to-domain conversion helpers."""

from __future__ import annotations

import json
from typing import Any

from app.library.domain.models import (
    Category,
    Resource,
    ResourceFile,
    ResourceStatus,
    ResourceType,
    StorageKind,
    WorkCatalog,
)
from app.library.infrastructure.media_paths import (
    file_content_url as _file_content_url,
    media_path as _media_path,
)
from app.library.infrastructure.orm import CategoryRow, FileRow, ResourceRow


def _parse_extra(raw: str | None) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _catalog_from_extra(extra: dict[str, Any]) -> WorkCatalog | None:
    raw = extra.get("catalog")
    if not isinstance(raw, dict) or not raw:
        return None
    try:
        return WorkCatalog.model_validate(raw)
    except Exception:
        return None


def _dump_extra(resource: Resource) -> str:
    extra = dict(resource.extra or {})
    if resource.catalog is None:
        extra.pop("catalog", None)
    else:
        extra["catalog"] = resource.catalog.model_dump(mode="json", by_alias=True)
    return json.dumps(extra, ensure_ascii=False)


def _orm_to_resource(row: ResourceRow) -> Resource:
    """ORM 行 → 领域模型。"""
    extra = _parse_extra(row.extra)
    catalog = _catalog_from_extra(extra)
    rest = {k: v for k, v in extra.items() if k != "catalog"}
    return Resource(
        id=row.id,
        type=ResourceType(row.type),
        storage_kind=StorageKind(row.storage_kind or StorageKind.OWNED.value),
        title=row.title,
        description=row.description,
        synopsis=row.synopsis,
        catalog=catalog,
        author=row.author,
        rating=row.rating,
        cover_path=_media_path(row.cover_path),
        status=ResourceStatus(row.status),
        deleted_at=row.deleted_at,
        last_scraped_at=row.last_scraped_at,
        scraped_source=row.scraped_source,
        extra=rest,
        timeline_visible=(
            None if row.timeline_visible is None else bool(row.timeline_visible)
        ),
        map_visible=(
            None if row.map_visible is None else bool(row.map_visible)
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def orm_to_resource(row: ResourceRow) -> Resource:
    return _orm_to_resource(row)


def _category_to_domain(row: CategoryRow) -> Category:
    return Category(
        id=row.id,
        name=row.name,
        type=ResourceType(row.type),
        parent_id=row.parent_id,
        sort=row.sort,
        is_system=bool(row.is_system),
    )


def _file_to_domain(f: FileRow) -> ResourceFile:
    """FileRow → 领域文件（详情与列表 primary 共用）。"""
    return ResourceFile(
        id=f.id,
        resource_id=f.resource_id,
        path=f.path,
        content_url=_file_content_url(f.resource_id, int(f.id)) if f.id is not None else None,
        sha256=f.sha256,
        size=f.size,
        format=f.format,
        role=f.role,
        duration=f.duration,
        width=f.width,
        height=f.height,
        codec=f.codec,
        fps=f.fps,
        bitrate=f.bitrate,
        exif_taken_at=f.exif_taken_at,
        exif_lat=f.exif_lat,
        exif_lng=f.exif_lng,
        exif_camera=f.exif_camera,
        exif_lens=f.exif_lens,
        exif_iso=f.exif_iso,
        exif_aperture=f.exif_aperture,
        exif_shutter=f.exif_shutter,
        created_at=f.created_at,
    )
