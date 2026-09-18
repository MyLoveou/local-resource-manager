"""网格缩略图：Pillow 缩放后写入包内 thumbs/grid.webp。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.shared.log import logger
from app.library.domain.type_profile import profile_for
from app.shared.media_types import FILE_ROLE_COVER, FILE_ROLE_PRIMARY, THUMB_MAX_EDGE_PX, THUMB_WEBP_QUALITY
from app.shared.models import ResourceType


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
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        with Image.open(source) as image:
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
