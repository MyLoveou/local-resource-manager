"""把静态图写入包内 cover 并刷新缩略图。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.library.application.covers.origin import (
    is_user_locked,
    merge_cover_origin,
)
from app.library.application.packages.resource_package import ResourcePackage
from app.library.infrastructure.repositories import ResourceRepository
from app.shared.log import logger
from app.shared.media_types import FILE_ROLE_COVER, FILE_ROLE_THUMBNAIL
from app.shared.models import Resource


async def attach_cover_image(
    resources: ResourceRepository,
    resource: Resource,
    package: ResourcePackage,
    src: Path,
    origin: str,
    *,
    honor_user_lock: bool = True,
    role_paths: dict[str, Path] | None = None,
    commit: bool = True,
) -> bool:
    """成功返回 True。honor_user_lock 时不覆盖用户封面。"""
    if resource.id is None:
        return False
    if honor_user_lock and is_user_locked(resource):
        return False
    try:
        dest = await asyncio.to_thread(package.put_cover, src)
        old = await resources.get_file_by_role(resource.id, FILE_ROLE_COVER)
        if old is not None:
            old_path = Path(old.path)
            if old_path.resolve() != dest.resolve() and old_path.is_file():
                await asyncio.to_thread(old_path.unlink)
            await resources.delete_file_row(old.id, commit=False)
        size = (await asyncio.to_thread(dest.stat)).st_size
        cover_row = await resources.add_file(
            resource.id,
            path=str(dest),
            sha256=None,
            size=size,
            format_=dest.suffix.lower().lstrip("."),
            role=FILE_ROLE_COVER,
            commit=False,
        )
        resource.cover_path = f"/library/resources/{resource.id}/files/{cover_row.id}/content"
        resource.extra = merge_cover_origin(resource.extra, origin)
        resource._touch()
        await resources.update(resource.id, resource, commit=False)
        if commit:
            await resources.commit()
        if role_paths is not None:
            role_paths[FILE_ROLE_COVER] = dest
        await _refresh_thumbnail(resources, resource.id, package, dest, commit=commit)
        return True
    except Exception as exc:
        logger.warning("写入封面失败 resource=%s: %s", resource.id, exc)
        try:
            await resources.rollback()
        except Exception:
            pass
        return False


async def _refresh_thumbnail(
    resources: ResourceRepository,
    resource_id: int,
    package: ResourcePackage,
    source_image: Path,
    *,
    commit: bool,
) -> None:
    try:
        thumb_dest = await asyncio.to_thread(package.put_thumbnail, source_image)
        if thumb_dest is None:
            return
        thumb_size = (await asyncio.to_thread(thumb_dest.stat)).st_size
        old_thumb = await resources.get_file_by_role(resource_id, FILE_ROLE_THUMBNAIL)
        if old_thumb is not None:
            # 新 file_id 才能换 thumbnailPath；同 URL 会被浏览器按 max-age=86400 缓存旧图。
            await resources.delete_file_row(old_thumb.id, commit=False)
        await resources.add_file(
            resource_id,
            path=str(thumb_dest),
            sha256=None,
            size=thumb_size,
            format_=thumb_dest.suffix.lower().lstrip("."),
            role=FILE_ROLE_THUMBNAIL,
            commit=commit,
        )
    except Exception as exc:
        logger.warning("换封面后缩略图失败 resource=%s: %s", resource_id, exc)
