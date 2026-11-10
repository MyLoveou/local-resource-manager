"""网格缩略图：Pillow 缩放后写入包内 thumbs/grid.webp。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageOps, UnidentifiedImageError

from app.shared.log import logger
from app.shared.image_support import register_optional_image_decoders
from app.library.domain.type_profile import profile_for
from app.library.domain.media_types import (
    FILE_ROLE_COVER,
    FILE_ROLE_PREVIEW,
    FILE_ROLE_PRIMARY,
    FILE_ROLE_THUMBNAIL,
    THUMB_MAX_EDGE_PX,
    THUMB_WEBP_QUALITY,
)
from app.library.domain.models import ResourceType

if TYPE_CHECKING:
    from app.library.application.packages.resource_package import ResourcePackage
    from app.library.infrastructure.repositories import ResourceRepository


def source_for_grid_thumbnail(type_: ResourceType, role_paths: dict[str, Path]) -> Path | None:
    """有封面用封面；cover_fallback 类型用主文件。"""
    cover = role_paths.get(FILE_ROLE_COVER)
    if cover is not None:
        return cover
    profile = profile_for(type_)
    if profile is not None and profile.cover_fallback:
        return role_paths.get(FILE_ROLE_PRIMARY)
    return None


def write_grid_thumbnail(source: Path, dest: Path) -> Path | None:
    """把源图缩到最大边后写成 WebP。失败返回 None，不留半文件。"""
    register_optional_image_decoders()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            image.load()
            frame = image.convert("RGBA") if image.mode in ("P", "RGBA", "LA") else image.convert("RGB")
            frame.thumbnail((THUMB_MAX_EDGE_PX, THUMB_MAX_EDGE_PX))
            save_mode = "RGBA" if frame.mode == "RGBA" else "RGB"
            frame.convert(save_mode).save(tmp, format="WEBP", quality=THUMB_WEBP_QUALITY, method=4)
        tmp.replace(dest)
        return dest
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        logger.warning("缩略图生成失败 %s: %s", source, exc)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return None


async def try_register_preview(
    resources: "ResourceRepository",
    resource_id: int,
    package: "ResourcePackage",
    role_paths: dict[str, Path],
) -> None:
    """HEIC/HEIF 额外写一份 jpg 预览；失败只记日志。"""
    primary = role_paths.get(FILE_ROLE_PRIMARY)
    if primary is None or primary.suffix.lower() not in {".heic", ".heif"}:
        return
    existing = await resources.get_file_by_role(resource_id, FILE_ROLE_PREVIEW)
    if existing is not None:
        return
    try:
        preview_dest = await asyncio.to_thread(package.put_preview, primary)
        if preview_dest is None:
            return
        size = (await asyncio.to_thread(preview_dest.stat)).st_size
        await resources.add_file(
            resource_id,
            path=str(preview_dest),
            sha256=None,
            size=size,
            format_="jpg",
            role=FILE_ROLE_PREVIEW,
            commit=True,
        )
    except Exception as exc:
        logger.warning("预览图登记失败 resource=%s: %s", resource_id, exc)
        await resources.rollback()


async def try_register_thumbnail(
    resources: "ResourceRepository",
    resource_id: int,
    package: "ResourcePackage",
    type_: ResourceType,
    role_paths: dict[str, Path],
) -> None:
    """缩略图失败只记日志，不回滚已复制的资源。"""
    await try_register_preview(resources, resource_id, package, role_paths)
    thumb_src = source_for_grid_thumbnail(type_, role_paths)
    if thumb_src is None:
        return
    existing_thumb = await resources.get_file_by_role(resource_id, FILE_ROLE_THUMBNAIL)
    if existing_thumb is not None:
        return
    try:
        thumb_dest = await asyncio.to_thread(package.put_thumbnail, thumb_src)
        if thumb_dest is None:
            return
        thumb_size = (await asyncio.to_thread(thumb_dest.stat)).st_size
        await resources.add_file(
            resource_id,
            path=str(thumb_dest),
            sha256=None,
            size=thumb_size,
            format_=thumb_dest.suffix.lower().lstrip("."),
            role=FILE_ROLE_THUMBNAIL,
            commit=True,
        )
    except Exception as exc:
        logger.warning("缩略图登记失败 resource=%s: %s", resource_id, exc)
        await resources.rollback()
